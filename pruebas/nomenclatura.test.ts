import assert from 'node:assert/strict';
import { test } from 'node:test';
import { importarDibsa } from '../src/nucleo/importar-dibsa.ts';
import { agujeroChumacera, leerNomenclatura, manguitoPulgadasAMm } from '../src/nucleo/nomenclatura.ts';

const datos = (np: string, marca = 'FAG', cat = 'RODAMIENTO') => leerNomenclatura(np, marca, cat).datos;
const publica = (np: string, marca = 'FAG', cat = 'RODAMIENTO') => leerNomenclatura(np, marca, cat).publicar;

test('ficha: solo los datos de la pieza', () => {
  assert.deepEqual(datos('22322E1AMC3'), ['Jaula de latón', 'Juego interno C3']);
  assert.deepEqual(datos('NU212ETVP2C3', 'NBI'), ['Jaula de poliamida', 'Juego interno C3']);
  assert.deepEqual(datos('62052RSR'), ['Sellos de hule en ambos lados']);
  assert.deepEqual(datos('62052Z'), ['Tapas metálicas en ambos lados']);
  assert.deepEqual(datos('6205'), []);
  assert.deepEqual(datos('22220EK', 'SKF'), ['Agujero cónico']);
});

test('temperaturas', () => {
  assert.deepEqual(datos('6309FT150', 'SNR'), ['Para temperatura de hasta 150 °C']);
  assert.deepEqual(datos('6204HT2002Z', 'SNR'), ['Para temperatura de hasta 200 °C', 'Tapas metálicas en ambos lados']);
  assert.deepEqual(datos('6008F600', 'SNR'), ['Para temperatura de hasta 300 °C']);
  assert.deepEqual(datos('6008F604', 'SNR'), ['Para temperatura de hasta 300 °C']);
});

test('rodamientos que no se publican', () => {
  assert.equal(publica('60/22', 'SKF'), false);
  assert.equal(publica('54208'), false);
  assert.equal(publica('543085-2', 'TIMKEN'), true); // no es serie 54
  assert.equal(publica('HC71914EDLRTP4SUL'), false);
});

test('series 52 y 53 usan medidas de 32 y 33', () => {
  assert.equal(leerNomenclatura('5202K', 'FAFNIR', 'RODAMIENTO').codigoParaMedidas, '3202K');
  assert.equal(leerNomenclatura('5306JC3', 'NSK', 'RODAMIENTO').codigoParaMedidas, '3306JC3');
  assert.equal(leerNomenclatura('5358', 'TIMKEN', 'RODAMIENTO').codigoParaMedidas, undefined);
});

test('casquillos HK/BK: diametro exterior por tabla', () => {
  assert.deepEqual(leerNomenclatura('HK1516', 'INA', 'RODAMIENTO').medidas, { agujeroMm: 15, exteriorMm: 21, anchoMm: 16 });
  assert.equal(leerNomenclatura('BK0306TN', 'INA', 'RODAMIENTO').medidas?.exteriorMm, 6);
  assert.equal(leerNomenclatura('HK6032', 'INA', 'RODAMIENTO').medidas?.exteriorMm, 68);
});

test('chumaceras: tipo, material y agujero', () => {
  const n = leerNomenclatura('UCP216-50', 'FAG', 'CHUMACERA');
  assert.equal(n.tipo, 'Chumacera de pedestal');
  assert.equal(n.medidas?.agujeroMm, 79.375);
  assert.deepEqual(agujeroChumacera(50), { pulgadas: '3 1/8"', mm: 79.375 });
  assert.equal(agujeroChumacera(16).pulgadas, '1"');
  assert.equal(leerNomenclatura('UCFL210', 'X', 'CHUMACERA').tipo, 'Chumacera de brida ovalada');
  assert.equal(leerNomenclatura('UCFC210-30', 'X', 'CHUMACERA').tipo, 'Chumacera de brida cuadrada corta');
  assert.equal(leerNomenclatura('UCT205', 'X', 'CHUMACERA').tipo, 'Chumacera tensora');
  assert.deepEqual(datos('SSUCP212', 'TRANSLINK', 'CHUMACERA'), ['Acero inoxidable', 'Agujero de 60 mm']);
  assert.deepEqual(datos('UCTP208', 'TRANSLINK', 'OTROS'), ['Caja termoplástica', 'Agujero de 40 mm']);
  assert.deepEqual(datos('UCFX12-38', 'ISB', 'CHUMACERA'), ['Versión reforzada', 'Agujero de 2 3/8" (60.325 mm)']);
  assert.deepEqual(datos('UKF208', 'TRANSLINK', 'CHUMACERA'), ['Agujero cónico', 'Se monta con manguito H2308 (se vende aparte)']);
  assert.equal(publica('UCPH209', 'ISB', 'CHUMACERA'), false);
  assert.equal(publica('UCC207D1', 'NSK', 'OTROS'), false);
});

test('SNL es solo la caja y TSNG no es chumacera', () => {
  const snl = leerNomenclatura('SNL516/613', 'SNR', 'CHUMACERA');
  assert.equal(snl.publicar, true);
  assert.deepEqual(snl.datos, ['Solo la caja bipartida: no incluye rodamiento, buje ni sello']);
  assert.notEqual(leerNomenclatura('TSNG509', 'TRANSLINK', 'OTROS').categoria, 'CHUMACERA');
});

test('manguitos', () => {
  assert.equal(leerNomenclatura('HA2322', 'TRANSLINK', 'BUJE').tipo, 'Manguito de fijación');
  assert.equal(leerNomenclatura('H3124403', 'FAG', 'ACCESORIO').codigoSchaeffler, 'H3124X403');
  assert.equal(leerNomenclatura('H 2309.107', 'FAG', 'ACCESORIO').codigoSchaeffler, 'H2309X107');
  assert.equal(publica('HM3044', 'FAG', 'ACCESORIO'), false);
  assert.equal(publica('HM907643', 'TIMKEN', 'RODAMIENTO'), true); // cono Timken, no tuerca
  assert.equal(manguitoPulgadasAMm(1.6875), 43);
  assert.equal(manguitoPulgadasAMm(1.4375), 36.5);
});

test('cadenas: caja de 3.05 m', () => {
  assert.deepEqual(datos('CADENA40-2R', 'ISB', 'CADENA'), ['Doble hilera', 'Caja de 3.05 m']);
  assert.deepEqual(datos('CADENA12-B1SS', 'ISB', 'OTROS'), ['Sencilla', 'Acero inoxidable', 'Caja de 3.05 m']);
  assert.deepEqual(datos('CADENA60-1R(5MTS)', 'ISB', 'OTROS'), ['Sencilla', 'Caja de 5 m']);
});

test('importacion: J7 se une con la version con guion, sin J7 en el nombre', () => {
  const csv = `"ID_PRODUCTO","MARCA","DESCRIPCION","PRECIO_UNITARIO","PU","CDMX","QUERETARO","SLP","PUEBLA","LEON","MONTERREY","TOLUCA","GUADALAJARA","TORREON","SALTILLO","VERACRUZ"
"UCP205-16-J7","FAG","CHUMACERA FAG",300,"",2,0,0,0,0,0,0,0,0,0,0
"UCP205-16","FAG","CHUMACERA FAG",310,"",0,5,0,0,0,0,0,0,0,0,0
"60/22","SKF","RODAMIENTO SKF",100,"",1,0,0,0,0,0,0,0,0,0,0
"PJ711-5","OPTIBELT","OPTIBELT",100,"",1,0,0,0,0,0,0,0,0,0,0
`;
  const r = importarDibsa(csv);
  const ch = r.productos.find((p) => p.marca === 'FAG')!;
  assert.equal(r.productos.length, 3);
  assert.equal(ch.numeroDeParte, 'UCP205-16');
  assert.deepEqual(ch.otrosNombres, ['UCP205-16-J7']);
  assert.equal(ch.existenciaTotal, 7);
  assert.equal(r.productos.find((p) => p.marca === 'SKF')!.publicar, false);
  assert.equal(r.productos.find((p) => p.marca === 'OPTIBELT')!.publicar, true); // J7 de bandas no se toca
});

test('diagonal: solo se ignoran los de serie/diametro', () => {
  assert.equal(publica('62/28DDU', 'NSK'), false);
  assert.equal(publica('320/32X', 'FAG'), false);
  assert.equal(publica('580/572', 'TIMKEN', 'OTROS'), true);
  assert.equal(publica('CF1/2NS', 'MC GILL'), true);
  assert.deepEqual(datos('22206CCC3/W33', 'TRANSLINK'), ['Juego interno C3', 'Ranura y orificios de lubricación en el aro exterior']);
});

const tipo = (np: string, marca = 'FAG', cat = 'RODAMIENTO', desc = '') => leerNomenclatura(np, marca, cat, desc).tipo;

test('rodamientos de bolas fuera de la serie ISO de 2 cifras', () => {
  assert.equal(tipo('62208A2RSR'), 'Rodamiento rígido de bolas');
  assert.equal(tipo('630062RS', 'ISB'), 'Rodamiento rígido de bolas');
  assert.equal(tipo('617072RS', 'ISB'), 'Rodamiento rígido de bolas');
  assert.deepEqual(datos('6882RS', 'TRANSLINK'), ['Sellos de hule en ambos lados']);
  assert.equal(tipo('69052RS', 'TRANSLINK'), 'Rodamiento rígido de bolas');
  assert.equal(tipo('608', 'FAG'), 'Rodamiento rígido de bolas');
  assert.deepEqual(datos('629C2ZC3', 'FAG'), ['Tapas metálicas en ambos lados', 'Juego interno C3']);
  assert.deepEqual(datos('R6-2Z', 'NB'), ['Tapas metálicas en ambos lados']);
  assert.equal(tipo('R12', 'TRANSLINK'), 'Rodamiento rígido de bolas');
  assert.equal(tipo('R16110', 'SNR', 'OTROS'), undefined); // kit SNR, no es R en pulgadas
  assert.deepEqual(leerNomenclatura('SS-63052RS', 'TRANSLINK', 'RODAMIENTO').datos, ['Acero inoxidable', 'Sellos de hule en ambos lados']);
  assert.equal(tipo('F6072Z', 'TRANSLINK'), 'Rodamiento rígido de bolas con brida');
  assert.equal(tipo('F19119', 'FERSA'), undefined);
  assert.equal(tipo('MR1052ZSS', 'ISB'), 'Rodamiento rígido de bolas');
  assert.equal(tipo('MR24S', 'MC GILL'), 'Rodamiento de agujas');
  assert.equal(tipo('4205ATN9C3', 'ISB'), 'Rodamiento rígido de bolas de dos hileras');
  assert.equal(tipo('11205TVH'), 'Rodamiento de bolas autoalineable');
});

test('contacto angular, cuatro puntos y axiales', () => {
  assert.equal(tipo('7416BMP'), 'Rodamiento de bolas de contacto angular');
  assert.equal(tipo('71805TN', 'INA'), 'Rodamiento de bolas de contacto angular');
  assert.equal(tipo('HCS71913ETP4SDUL'), 'Rodamiento de bolas de contacto angular');
  assert.equal(tipo('2MM208WIDUL', 'FAFNIR'), 'Rodamiento de bolas de contacto angular');
  assert.equal(tipo('3801B2ZTVH'), 'Rodamiento de bolas de contacto angular de dos hileras');
  assert.equal(tipo('QJ216N2MA', 'ISB'), 'Rodamiento de bolas de contacto de cuatro puntos');
  assert.equal(tipo('52209', 'ISB'), 'Rodamiento axial de bolas');
  assert.equal(tipo('5209', 'ISB'), 'Rodamiento de bolas de contacto angular de dos hileras');
  assert.equal(tipo('234420MSP'), 'Rodamiento axial de bolas de contacto angular');
  assert.equal(tipo('89412TV', 'INA'), 'Rodamiento axial de rodillos cilíndricos');
  assert.equal(tipo('K81128TV', 'INA', 'OTROS'), 'Corona axial de rodillos');
  assert.equal(tipo('AXK4060', 'ISB', 'OTROS'), 'Corona axial de agujas');
  assert.equal(tipo('GS81113', 'INA', 'OTROS'), 'Arandela axial');
  assert.equal(tipo('23324E1AXLMA1T41A'), 'Rodamiento de rodillos esféricos');
  assert.equal(tipo('23322E1AXLMA1T41A'), 'Rodamiento de rodillos esféricos');
});

test('agujas, cilindricos de llenado completo y seguidores', () => {
  assert.equal(tipo('NKX10ZTV', 'ISB'), 'Rodamiento de agujas combinado');
  assert.equal(tipo('RNAO40X50X17', 'INA'), 'Rodamiento de agujas');
  assert.equal(tipo('ZARN2062LTV', 'INA'), 'Rodamiento combinado de agujas y rodillos axiales');
  assert.equal(tipo('ZKLF12552RSPE', 'INA'), 'Rodamiento axial de bolas de contacto angular para husillo');
  assert.equal(tipo('K28X33X13', 'ISB', 'OTROS'), 'Corona de agujas');
  assert.equal(tipo('NRB6X22', 'INA'), 'Agujas sueltas');
  assert.equal(tipo('SCE105', 'INA'), 'Casquillo de agujas');
  assert.equal(tipo('SL045024PP', 'INA'), 'Rodamiento de rodillos cilíndricos de llenado completo');
  assert.equal(tipo('CF1/2NS', 'MC GILL'), 'Seguidor de leva con perno');
  assert.equal(tipo('KR19X-SK-PPA', 'INA'), 'Seguidor de leva con perno');
  assert.equal(tipo('NATR25PPA', 'ISB'), 'Rodillo seguidor tipo yugo');
  assert.equal(tipo('LR52002RS', 'ISB'), 'Rodillo de apoyo');
  assert.equal(tipo('MI18', 'MC GILL'), 'Pista interior para rodamiento de agujas');
  assert.deepEqual(datos('MCFR16B', 'MC GILL'), []);
});

test('insertos, rotulas, mazas, conos y tazas, lineales y balas', () => {
  assert.equal(tipo('GE25KRRB', 'NKE'), 'Rodamiento de inserto para chumacera');
  assert.equal(tipo('RA106NPPB', 'INA'), 'Rodamiento de inserto para chumacera');
  assert.equal(tipo('G1110KRR', 'TIMKEN'), 'Rodamiento de inserto para chumacera');
  assert.equal(tipo('W208PP', 'TIMKEN'), 'Rodamiento de inserto para chumacera');
  assert.equal(tipo('GE10E', 'ISB', 'ROTULA'), 'Rótula radial');
  assert.equal(tipo('PHSB16', 'TRANSLINK', 'ROTULA'), 'Terminal de rótula');
  assert.equal(tipo('GAR20UK2RS', 'INA', 'ROTULA'), 'Terminal de rótula');
  assert.equal(tipo('713240010'), 'Maza de rueda');
  assert.equal(tipo('101779', 'FAG', 'RODAMIENTO', 'MAZA FAG'), 'Maza de rueda');
  assert.equal(tipo('596', 'TIMKEN', 'RODAMIENTO', 'CONO TIMKEN'), 'Cono de rodamiento de rodillos cónicos');
  assert.equal(tipo('27620', 'TIMKEN', 'RODAMIENTO', 'TAZA TIMKEN'), 'Taza de rodamiento de rodillos cónicos');
  assert.equal(tipo('861', 'TIMKEN', 'RODAMIENTO', 'CONO Y TAZA TIMKEN'), 'Juego de cono y taza');
  assert.equal(tipo('SET30', 'TIMKEN'), 'Juego de cono y taza');
  assert.deepEqual(leerNomenclatura('596', 'TIMKEN', 'RODAMIENTO', 'CONO TIMKEN').datos, []);
  assert.equal(tipo('KHM88542/88510', 'FERSA'), 'Juego de cono y taza');
  assert.deepEqual(leerNomenclatura('KLM300849RG/811RG', 'NSK', 'RODAMIENTO').datos, []);
  assert.equal(tipo('KWVE35BSLG1V2', 'INA', 'OTROS'), 'Carro de guía lineal');
  assert.equal(tipo('GR1-060', 'ROSA', 'OTROS', 'GUIA LINEAL ROSA'), 'Guía lineal');
  assert.equal(tipo('BALAS10-G100SS', 'SNR', 'OTROS'), 'Balas (esferas) sueltas');
});

test('miniaturas de 3 cifras con sello doble', () => {
  assert.deepEqual(datos('6082RS', 'ISB'), ['Sellos de hule en ambos lados']);
  assert.deepEqual(datos('6262ZC3', 'ISB'), ['Tapas metálicas en ambos lados', 'Juego interno C3']);
  assert.deepEqual(datos('62052RS', 'ISB'), ['Sellos de hule en ambos lados']);
  assert.deepEqual(datos('6202RS', 'ISB'), ['Sello de hule en un lado']);
});

test('ronda 2, arreglo 1: husillo FAG: UM/DUM no es jaula de laton', () => {
  assert.ok(!datos('B7018ETP4SUM').includes('Jaula de latón'));
  assert.ok(!datos('B7009CTP4SDUM').includes('Jaula de latón'));
  assert.ok(!datos('B7008C2RSDTP4SUM').includes('Jaula de latón'));
});

test('ronda 2, arreglo 2: SL llenado completo: PP2 no es P2, PPZ no es tapa', () => {
  assert.deepEqual(datos('SL045012PP2NR', 'INA'), ['Con ranura y anillo de retención']);
  assert.deepEqual(datos('SL045014PPZNR', 'INA'), ['Con ranura y anillo de retención']);
});

test('ronda 2, arreglo 3: J + numero no es jaula de acero', () => {
  assert.ok(!datos('7005CVDUJ74', 'SNR').includes('Jaula de acero'));
  assert.ok(!datos('4308J30', 'SNR').includes('Jaula de acero'));
  assert.ok(!datos('6205EEJ30', 'SNR').includes('Jaula de acero'));
  assert.ok(!datos('52205J9', 'ISB').includes('Jaula de acero'));
  assert.deepEqual(datos('6205J', 'SNR'), ['Jaula de acero']);
});

test('ronda 2, arreglo 4: NSK MC3', () => {
  assert.ok(!datos('607DDMC3E', 'NSK').includes('Jaula de latón'));
  assert.ok(!datos('608DDMC3E', 'NSK').includes('Juego interno C3'));
  assert.deepEqual(datos('6282ZMC3E', 'NSK'), ['Tapas metálicas en ambos lados']);
});

test('ronda 2, arreglo 5: ISB MAX', () => {
  assert.deepEqual(datos('38022RSVMAX', 'ISB'), ['Sellos de hule en ambos lados']);
});

test('ronda 2, arreglo 6: FAG generacion C antes del sello', () => {
  assert.deepEqual(datos('6000C2HRSL038C3'), ['Sellos de hule en ambos lados', 'Juego interno C3']);
});

test('ronda 2, arreglo 7: la descripcion manda en conos', () => {
  assert.equal(tipo('665', 'FERSA', 'RODAMIENTO', 'CONO FERSA'), 'Cono de rodamiento de rodillos cónicos');
});

test('ronda 2, arreglo 8: SA202 no es rotula, SA10E si', () => {
  assert.equal(tipo('SA10E', 'ISB', 'ROTULA'), 'Terminal de rótula');
  assert.equal(tipo('SA202', 'ISB', 'ROTULA'), undefined);
});

test('ronda 2, arreglo 9: sello doble tras el 2 final', () => {
  assert.equal(tipo('32032RSE'), 'Rodamiento de bolas de contacto angular de dos hileras');
  assert.deepEqual(datos('32032RSE'), ['Sellos de hule en ambos lados']);
  assert.deepEqual(datos('NA2262RSR', 'INA'), ['Sellos de hule en ambos lados']);
});
