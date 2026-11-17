// Valores de negocio de DICOM. En la plataforma final viven en la base de datos
// y se editan desde el panel; estos son los valores iniciales.

export const IVA = 0.16;

// Costo = precio publicado por DIBSA x factor de la marca (uso interno).
export const FACTOR_POR_DEFECTO = 1.0;
export const FACTORES_POR_MARCA: Record<string, number> = {
  FAG: 0.7695,
  INA: 0.7695,
  SNR: 0.9,
  NKE: 0.9,
  JNS: 0.9,
  SMITH: 0.9,
  FERSA: 0.9,
  NBI: 0.9,
  NB: 0.9,
  CRI: 0.9,
  TRANSLINK: 0.9,
  TIMKEN: 0.9,
  'MC GILL': 0.95,
  MARTIN: 1.1,
};

// PROVISIONAL: la utilidad aun no la define la persona. Editable desde el panel.
export const UTILIDAD_POR_DEFECTO = 0.2;
export const UTILIDAD_ES_PROVISIONAL = true;

// Marcas cuya existencia sale del inventario propio de DICOM y no de DIBSA.
export const MARCAS_INVENTARIO_PROPIO = new Set(['ISB']);

// Marcas que no se venden directo: se muestran con "Consultar tiempo de entrega".
export const MARCAS_SOLO_CONSULTA = new Set(['MARTIN']);
// De Martin solo se publica lo comun.
export const CATEGORIAS_MARTIN_PERMITIDAS = new Set(['BUJE', 'POLEA', 'CATARINA']);

export const SUCURSAL_LOCAL = 'CDMX';
export const SUCURSALES = [
  'CDMX', 'QUERETARO', 'SLP', 'PUEBLA', 'LEON', 'MONTERREY',
  'TOLUCA', 'GUADALAJARA', 'TORREON', 'SALTILLO', 'VERACRUZ',
] as const;

export const ZONA_HORARIA = 'America/Mexico_City';
export const HORA_CORTE_ENVIO = 14; // pedidos pagados antes de las 2:00 pm salen hoy
export const PESO_MAXIMO_ENVIO_GRATIS_KG = 35;

// Actualizacion desde DIBSA: lunes a viernes, dentro de 8:00-18:00.
export const HORAS_SINCRONIZACION = [8, 12, 16];
export const URL_ARCHIVO_DIBSA = 'https://dibsamexico.com/wp-content/stock.csv';

// Codigos con "/". false: solo se ignoran los de serie/diametro en mm (60/22,
// 62/28, 320/32). true: se ignora todo codigo de rodamiento con "/" (tambien
// juegos cono/taza como 580/572, medidas en pulgadas como CF1/2 y sufijos C3/W33).
export const IGNORAR_TODO_CODIGO_CON_DIAGONAL = false;
