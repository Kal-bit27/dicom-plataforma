-- Estructura de la base de datos de la plataforma DICOM (PostgreSQL / Supabase).
-- Importes en pesos mexicanos, sin IVA salvo que el nombre diga lo contrario.

create table configuracion (
  clave        text primary key,
  valor        jsonb not null,
  actualizado  timestamptz not null default now()
);
-- Valores iniciales editables desde el panel.
insert into configuracion (clave, valor) values
  ('iva', '0.16'),
  ('utilidad_por_defecto', '0.20'),            -- PROVISIONAL, por definir
  ('factor_por_defecto', '1.00'),
  ('sucursal_local', '"CDMX"'),
  ('hora_corte_envio', '14'),
  ('peso_maximo_envio_gratis_kg', '35'),
  ('horas_sincronizacion', '[8, 12, 16]'),
  ('correo_avisos', 'null');                   -- por definir

create table marcas (
  id                  bigint generated always as identity primary key,
  nombre              text not null unique,
  factor              numeric(8,4) not null default 1.0 check (factor > 0),  -- uso interno
  utilidad            numeric(6,4) check (utilidad >= 0),   -- null = usa la general
  inventario_propio   boolean not null default false,       -- ISB
  solo_consulta       boolean not null default false,       -- Martin
  destacada           boolean not null default false
);
insert into marcas (nombre, factor, inventario_propio, solo_consulta) values
  ('FAG', 0.7695, false, false), ('INA', 0.7695, false, false),
  ('SNR', 0.90, false, false), ('NKE', 0.90, false, false), ('JNS', 0.90, false, false),
  ('SMITH', 0.90, false, false), ('FERSA', 0.90, false, false), ('NBI', 0.90, false, false),
  ('NB', 0.90, false, false), ('CRI', 0.90, false, false), ('TRANSLINK', 0.90, false, false),
  ('TIMKEN', 0.90, false, false), ('MC GILL', 0.95, false, false),
  ('MARTIN', 1.10, false, true), ('ISB', 1.00, true, false);

-- Medidas compartidas entre marcas: se guardan una vez por designacion base.
create table designaciones (
  id                bigint generated always as identity primary key,
  designacion       text not null unique,          -- ej. 6205-2RS
  diametro_interior numeric(10,3),
  diametro_exterior numeric(10,3),
  ancho             numeric(10,3),
  peso_kg           numeric(10,3),
  fuente            text                           -- de donde salio la medida
);

create table productos (
  id                 bigint generated always as identity primary key,
  marca_id           bigint not null references marcas(id),
  numero_de_parte    text not null,
  clave_busqueda     text not null,                -- sin guiones ni espacios
  descripcion        text not null default '',
  categoria          text not null default 'OTROS',
  designacion_id     bigint references designaciones(id),
  precio_dibsa       numeric(12,2) check (precio_dibsa > 0),
  factor             numeric(8,4) check (factor > 0),       -- null = el de la marca
  utilidad           numeric(6,4) check (utilidad >= 0),    -- null = marca o general
  envio_estimado     numeric(12,2) not null default 0 check (envio_estimado >= 0),
  peso_kg            numeric(10,3),                -- null = usa el de la designacion
  clave_sat          text,                         -- clave de producto para CFDI
  unidad_sat         text not null default 'H87',  -- pieza
  foto_url           text,
  publicado          boolean not null default true,
  actualizado_dibsa  timestamptz,
  unique (marca_id, numero_de_parte)
);
create index productos_clave_busqueda on productos (clave_busqueda text_pattern_ops);
create index productos_categoria on productos (categoria);

-- Existencia de DIBSA por sucursal. Se reemplaza en cada actualizacion.
create table existencias_dibsa (
  producto_id  bigint not null references productos(id) on delete cascade,
  sucursal     text not null,
  cantidad     integer not null check (cantidad >= 0),
  primary key (producto_id, sucursal)
);

-- Inventario propio de DICOM (hoy: ISB). Solo cambia por ajuste manual o venta.
create table inventario_propio (
  producto_id  bigint primary key references productos(id) on delete cascade,
  cantidad     integer not null default 0 check (cantidad >= 0)
);

-- Bitacora: cada cambio de existencia propia queda escrito y no se borra.
create table bitacora_inventario (
  id                 bigint generated always as identity primary key,
  producto_id        bigint not null references productos(id),
  cantidad_anterior  integer not null,
  cantidad_nueva     integer not null check (cantidad_nueva >= 0),
  motivo             text not null check (length(trim(motivo)) > 0),
  origen             text not null check (origen in ('AJUSTE_MANUAL', 'VENTA_EN_LINEA', 'CARGA_ARCHIVO', 'CANCELACION')),
  usuario            text not null,
  pedido_id          bigint,
  fecha              timestamptz not null default now()
);
create rule bitacora_sin_cambios as on update to bitacora_inventario do instead nothing;
create rule bitacora_sin_borrados as on delete to bitacora_inventario do instead nothing;

-- Ajuste manual seguro: se escribe la existencia NUEVA y se indica la que se
-- esta viendo. Si otra venta la cambio mientras tanto, el ajuste se rechaza.
create function ajustar_inventario(
  p_producto bigint, p_esperada integer, p_nueva integer, p_motivo text, p_usuario text
) returns void language plpgsql as $$
declare v_actual integer;
begin
  select cantidad into v_actual from inventario_propio where producto_id = p_producto for update;
  if not found then
    v_actual := 0;
    insert into inventario_propio (producto_id, cantidad) values (p_producto, 0);
  end if;
  if v_actual <> p_esperada then
    raise exception 'La existencia cambio (ahora es %). Revisa y vuelve a intentar.', v_actual;
  end if;
  update inventario_propio set cantidad = p_nueva where producto_id = p_producto;
  insert into bitacora_inventario (producto_id, cantidad_anterior, cantidad_nueva, motivo, origen, usuario)
  values (p_producto, v_actual, p_nueva, p_motivo, 'AJUSTE_MANUAL', p_usuario);
end $$;

-- Registro de cada actualizacion desde DIBSA.
create table sincronizaciones (
  id                bigint generated always as identity primary key,
  inicio            timestamptz not null default now(),
  fin               timestamptz,
  estado            text not null default 'EN_CURSO' check (estado in ('EN_CURSO', 'CORRECTA', 'FALLIDA')),
  renglones_leidos  integer,
  productos         integer,
  precios_cambiados integer,
  error             text
);

create table clientes (
  id       bigint generated always as identity primary key,
  correo   text not null unique,
  nombre   text not null,
  telefono text,
  creado   timestamptz not null default now()
);

create table perfiles_fiscales (
  id              bigint generated always as identity primary key,
  cliente_id      bigint not null references clientes(id) on delete cascade,
  rfc             text not null,
  razon_social    text not null,
  regimen_fiscal  text not null,
  codigo_postal   text not null,
  uso_cfdi        text not null
);

create table pedidos (
  id               bigint generated always as identity primary key,
  folio            text not null unique,
  cliente_id       bigint references clientes(id),      -- null = compra como invitado
  correo           text not null,
  nombre           text not null,
  telefono         text,
  direccion_envio  jsonb not null,
  estado           text not null default 'PENDIENTE_DE_PAGO'
                   check (estado in ('PENDIENTE_DE_PAGO', 'PAGADO', 'ENVIADO', 'ENTREGADO', 'CANCELADO')),
  subtotal         numeric(12,2) not null,
  iva              numeric(12,2) not null,
  total            numeric(12,2) not null,
  costo_total      numeric(12,2) not null,              -- interno
  envio_estimado   numeric(12,2) not null default 0,    -- interno
  comision_cobro   numeric(12,2) not null default 0,    -- interno
  utilidad         numeric(12,2),                       -- interno
  pago_id          text,                                -- identificador en Mercado Pago
  paqueteria       text,
  guia             text,
  perfil_fiscal_id bigint references perfiles_fiscales(id),
  factura_uuid     text,
  creado           timestamptz not null default now(),
  pagado           timestamptz
);

create table pedido_renglones (
  id               bigint generated always as identity primary key,
  pedido_id        bigint not null references pedidos(id) on delete cascade,
  producto_id      bigint not null references productos(id),
  numero_de_parte  text not null,
  marca            text not null,
  cantidad         integer not null check (cantidad > 0),
  precio_unitario  numeric(12,2) not null,   -- al cliente, sin IVA
  costo_unitario   numeric(12,2) not null,   -- interno
  aviso_entrega    text not null             -- ENVIA_HOY, MAYOR_TIEMPO, ...
);

-- Formulario "Consultar tiempo de entrega".
create table solicitudes_entrega (
  id           bigint generated always as identity primary key,
  nombre       text not null,
  correo       text not null,
  material     text not null,
  piezas       integer not null check (piezas > 0),
  producto_id  bigint references productos(id),
  atendida     boolean not null default false,
  creado       timestamptz not null default now()
);
