# Plataforma DICOM

Tienda en línea, cotizador y panel de administración de DICOM.

## Qué hay hasta ahora (fase 1, núcleo)

| Archivo | Qué hace |
| --- | --- |
| `src/nucleo/configuracion.ts` | Valores de negocio: factores por marca, IVA, corte de envío, tope de 35 kg, horario de actualización |
| `src/nucleo/precios.ts` | Costo (precio DIBSA × factor), precio de venta, IVA y utilidad por producto y por pedido |
| `src/nucleo/entrega.ts` | Avisos "se envía hoy", "mayor tiempo de entrega", "consultar", y envío gratis |
| `src/nucleo/importar-dibsa.ts` | Lee el archivo de DIBSA, une repetidos, deduce categoría y decide el horario de actualización |
| `db/esquema.sql` | Estructura de la base de datos (PostgreSQL / Supabase), con bitácora de inventario |
| `pruebas/nucleo.test.ts` | Pruebas automáticas de todas las reglas |

## Cómo probar

```
npm run pruebas
npm run importar -- ruta/al/stock.csv
```

Requiere Node 22.18 o superior. No hay dependencias que instalar.

## Pendiente de definir por DICOM

- Utilidad sobre el costo (hoy 20% provisional).
- Correo para avisos de pedido y solicitudes.
- Repositorio de GitHub, dominio y cuentas (Vercel, Supabase, Mercado Pago, PAC).

## Nomenclatura (2026-11-15)
`src/nucleo/nomenclatura.ts` lee cada número de parte y decide si se publica, con qué pieza se une (chumaceras J7), su tipo, medidas (agujero de chumaceras en pulgadas, casquillos HK/BK) y la lista de **datos de la ficha**: solo lo que aplica a esa pieza (por ejemplo "Jaula de latón", "Juego interno C3"), sin explicar códigos. Pruebas en `pruebas/nomenclatura.test.ts`. Interruptor para códigos con "/" en `configuracion.ts`.
