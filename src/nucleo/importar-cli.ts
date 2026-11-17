// Uso: node src/nucleo/importar-cli.ts ruta/al/stock.csv
import { readFileSync } from 'node:fs';
import { UTILIDAD_POR_DEFECTO } from './configuracion.ts';
import { importarDibsa } from './importar-dibsa.ts';
import { calcularPrecio } from './precios.ts';

const ruta = process.argv[2];
if (!ruta) { console.error('Falta la ruta del archivo CSV de DIBSA'); process.exit(1); }
const r = importarDibsa(readFileSync(ruta, 'utf8'));
const cuenta = (f: (p: (typeof r.productos)[number]) => boolean) => r.productos.filter(f).length;
const porCategoria: Record<string, number> = {};
const noPublicados: Record<string, number> = {};
for (const p of r.productos) {
  porCategoria[p.categoria] = (porCategoria[p.categoria] ?? 0) + 1;
  if (!p.publicar) noPublicados[p.motivoNoPublicar ?? 'Sin motivo'] = (noPublicados[p.motivoNoPublicar ?? 'Sin motivo'] ?? 0) + 1;
}

console.log(JSON.stringify({
  renglonesLeidos: r.renglonesLeidos,
  productos: r.productos.length,
  repetidosUnidos: r.repetidosUnidos,
  descartados: r.descartados.length,
  publicables: cuenta((p) => p.publicar),
  conExistencia: cuenta((p) => p.existenciaTotal > 0),
  conExistenciaEnCdmx: cuenta((p) => p.existenciaLocal > 0),
  soloEnOtrasSucursales: cuenta((p) => p.existenciaLocal === 0 && p.existenciaTotal > 0),
  porCategoria,
  noPublicados,
  unidosConOtroNombre: cuenta((p) => p.otrosNombres.length > 0),
  conDatosEnFicha: cuenta((p) => p.datos.length > 0),
}, null, 2));

console.log(`\nEjemplos con utilidad provisional de ${UTILIDAD_POR_DEFECTO * 100}%:`);
for (const [parte, marca] of [['62052RSR', 'FAG'], ['62052RS', 'TRANSLINK'], ['62052RSH', 'SKF'], ['62052RS', 'ISB']]) {
  const p = r.productos.find((x) => x.numeroDeParte === parte && x.marca === marca);
  if (!p) continue;
  const d = calcularPrecio({ precioDibsa: p.precioDibsa, marca: p.marca });
  console.log(`${marca} ${parte}: DIBSA ${p.precioDibsa} | costo ${d.costo} | venta ${d.precioVenta} + IVA = ${d.precioConIva} | utilidad ${d.utilidadPesos} | CDMX ${p.existenciaLocal} / total ${p.existenciaTotal}`);
}
