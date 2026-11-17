import assert from 'node:assert/strict';
import { test } from 'node:test';
import { avisoDeEntrega, avisoDeEnvio } from '../src/nucleo/entrega.ts';
import { categoriaDe, claveDeBusqueda, importarDibsa, leerCsv, tocaSincronizar } from '../src/nucleo/importar-dibsa.ts';
import { calcularPrecio, factorDeMarca, utilidadDePedido } from '../src/nucleo/precios.ts';

// Mexico centro es UTC-6 todo el año.
const mx = (iso: string) => new Date(`${iso}-06:00`);
const VIERNES_10AM = mx('2026-11-13T10:00:00');
const VIERNES_3PM = mx('2026-11-13T15:00:00');
const SABADO_10AM = mx('2026-11-14T10:00:00');

test('factores por marca', () => {
  assert.equal(factorDeMarca('FAG'), 0.7695);
  assert.equal(factorDeMarca('ina'), 0.7695);
  assert.equal(factorDeMarca('Translink'), 0.9);
  assert.equal(factorDeMarca('MC  GILL'), 0.95);
  assert.equal(factorDeMarca('MARTIN'), 1.1);
  assert.equal(factorDeMarca('SKF'), 1);
  assert.equal(factorDeMarca('ISB'), 1);
  assert.equal(factorDeMarca('MARCA NUEVA'), 1);
});

test('costo con precios reales de DIBSA', () => {
  assert.equal(calcularPrecio({ precioDibsa: 102.99, marca: 'FAG', utilidad: 0 }).costo, 79.25);
  assert.equal(calcularPrecio({ precioDibsa: 45.77, marca: 'TRANSLINK', utilidad: 0 }).costo, 41.19);
  assert.equal(calcularPrecio({ precioDibsa: 200.35, marca: 'SKF', utilidad: 0 }).costo, 200.35);
});

test('precio de venta: costo + utilidad + envio, mas IVA', () => {
  const d = calcularPrecio({ precioDibsa: 100, marca: 'SKF', utilidad: 0.25, envioEstimado: 10 });
  assert.equal(d.costo, 100);
  assert.equal(d.precioVenta, 135);
  assert.equal(d.iva, 21.6);
  assert.equal(d.precioConIva, 156.6);
  assert.equal(d.utilidadPesos, 25);
});

test('no se permite vender bajo costo', () => {
  assert.throws(() => calcularPrecio({ precioDibsa: 100, marca: 'SKF', utilidad: -0.1 }));
  assert.throws(() => calcularPrecio({ precioDibsa: 0, marca: 'SKF' }));
});

test('utilidad de un pedido descuenta costo, envio y comision', () => {
  const precio = calcularPrecio({ precioDibsa: 100, marca: 'SKF', utilidad: 0.25, envioEstimado: 10 });
  const u = utilidadDePedido([{ cantidad: 2, precio }], 0.04);
  assert.equal(u.subtotal, 270);
  assert.equal(u.total, 313.2);
  assert.equal(u.comision, 12.53);
  assert.equal(u.utilidad, 37.47);
});

test('entrega: se envia hoy solo si CDMX cubre toda la cantidad', () => {
  const base = { marca: 'FAG', existenciaLocal: 1, existenciaTotal: 3, ahora: VIERNES_10AM };
  assert.equal(avisoDeEntrega({ ...base, cantidad: 1 }), 'ENVIA_HOY');
  assert.equal(avisoDeEntrega({ ...base, cantidad: 3 }), 'MAYOR_TIEMPO'); // 1 en CDMX + 2 en sucursal
  assert.equal(avisoDeEntrega({ ...base, cantidad: 4 }), 'SIN_EXISTENCIA');
  assert.equal(avisoDeEntrega({ ...base, existenciaLocal: 0, cantidad: 1 }), 'MAYOR_TIEMPO'); // solo Toluca
});

test('entrega: corte de las 2 pm y dias habiles', () => {
  const base = { marca: 'FAG', cantidad: 1, existenciaLocal: 5, existenciaTotal: 5 };
  assert.equal(avisoDeEntrega({ ...base, ahora: mx('2026-11-13T13:59:00') }), 'ENVIA_HOY');
  assert.equal(avisoDeEntrega({ ...base, ahora: mx('2026-11-13T14:00:00') }), 'ENVIA_SIGUIENTE_DIA');
  assert.equal(avisoDeEntrega({ ...base, ahora: VIERNES_3PM }), 'ENVIA_SIGUIENTE_DIA');
  assert.equal(avisoDeEntrega({ ...base, ahora: SABADO_10AM }), 'ENVIA_SIGUIENTE_DIA');
});

test('Martin siempre es consultar', () => {
  assert.equal(avisoDeEntrega({ marca: 'Martin', cantidad: 1, existenciaLocal: 9, existenciaTotal: 9, ahora: VIERNES_10AM }), 'CONSULTAR');
});

test('envio gratis hasta 35 kg', () => {
  assert.equal(avisoDeEnvio(0.13), 'ENVIO_GRATIS');
  assert.equal(avisoDeEnvio(35), 'ENVIO_GRATIS');
  assert.equal(avisoDeEnvio(35.1), 'ENVIO_A_COTIZAR');
  assert.equal(avisoDeEnvio(null), 'PESO_POR_CONFIRMAR');
});

test('busqueda tolera guiones y espacios', () => {
  assert.equal(claveDeBusqueda('6205-2RS'), '62052RS');
  assert.equal(claveDeBusqueda('6205 2rs'), '62052RS');
  assert.equal(claveDeBusqueda('NK30/20TN'), 'NK3020TN');
});

test('categoria deducida de la descripcion', () => {
  assert.equal(categoriaDe('RODAMIENTO FAG'), 'RODAMIENTO');
  assert.equal(categoriaDe('RETEN VITON ISB'), 'RETEN');
  assert.equal(categoriaDe('CHUMACERA INA'), 'CHUMACERA');
  assert.equal(categoriaDe('BANDA JASON'), 'BANDA');
  assert.equal(categoriaDe('CATARINA MARTIN'), 'CATARINA');
  assert.equal(categoriaDe('POLEA MARTIN'), 'POLEA');
  assert.equal(categoriaDe('MARTIN'), 'OTROS');
});

const CSV = `﻿"ID_PRODUCTO","MARCA","DESCRIPCION","PRECIO_UNITARIO","PU","CDMX","QUERETARO","SLP","PUEBLA","LEON","MONTERREY","TOLUCA","GUADALAJARA","TORREON","SALTILLO","VERACRUZ"
"62052RSR","FAG","RODAMIENTO FAG",102.99,"MXN 102.99",41,0,0,0,147,0,4,0,0,0,0
"MR36N","MC GILL","RODAMIENTO MC GILL",927.46,"MXN 927.46",0,0,1,0,0,0,0,1,0,0,0
"MR36N","MC GILL","MC GILL",927.46,"MXN 927.46",4,2,0,2,0,0,0,0,0,0,0
"60B20","MARTIN","CATARINA MARTIN",1117,"MXN 1,117.00",0,0,0,0,0,0,0,0,0,0,0
"160B19","MARTIN","MARTIN",13945,"MXN 13,945.00",0,0,0,0,0,0,0,0,0,0,0
"62052RS","ISB","RODAMIENTO ISB",47.88,"MXN 47.88",339,0,0,0,0,2,34,0,0,1,309
"MALO","FAG","RODAMIENTO FAG",0,"MXN 0.00",1,0,0,0,0,0,0,0,0,0,0
`;

test('lector de CSV respeta comas dentro de comillas', () => {
  const filas = leerCsv(CSV);
  assert.equal(filas.length, 7);
  assert.equal(filas[3].PU, 'MXN 1,117.00');
});

test('importacion de DIBSA', () => {
  const r = importarDibsa(CSV);
  assert.equal(r.renglonesLeidos, 7);
  assert.equal(r.productos.length, 5);
  assert.equal(r.repetidosUnidos, 1);
  assert.equal(r.descartados.length, 1);

  const fag = r.productos.find((p) => p.numeroDeParte === '62052RSR')!;
  assert.equal(fag.existenciaLocal, 41);
  assert.equal(fag.existenciaTotal, 192);

  const mr = r.productos.find((p) => p.numeroDeParte === 'MR36N')!;
  assert.equal(mr.existencias.CDMX, 4);
  assert.equal(mr.existencias.SLP, 1);
  assert.equal(mr.existenciaTotal, 10);
  assert.equal(mr.descripcion, 'RODAMIENTO MC GILL');

  assert.equal(r.productos.find((p) => p.numeroDeParte === '60B20')!.publicar, true);
  assert.equal(r.productos.find((p) => p.numeroDeParte === '160B19')!.publicar, false);
  assert.equal(r.productos.find((p) => p.marca === 'ISB')!.existenciaDesdeInventarioPropio, true);
});

test('horario de actualizacion: lunes a viernes 8, 12 y 16 h', () => {
  assert.equal(tocaSincronizar(mx('2026-11-13T08:05:00')), true);
  assert.equal(tocaSincronizar(mx('2026-11-13T12:00:00')), true);
  assert.equal(tocaSincronizar(mx('2026-11-13T16:30:00')), true);
  assert.equal(tocaSincronizar(mx('2026-11-13T10:00:00')), false);
  assert.equal(tocaSincronizar(mx('2026-11-13T19:00:00')), false);
  assert.equal(tocaSincronizar(mx('2026-11-14T08:00:00')), false); // sabado
});
