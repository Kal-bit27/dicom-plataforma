// Reglas de nomenclatura que dio la persona (2026-11-15). A partir del numero
// de parte se decide: si la pieza se publica, con que otra se une (J7), su tipo,
// sus medidas y la lista de DATOS que ve el cliente en la ficha.
//
// Regla de la ficha: solo los datos que aplican a ESA pieza ("Jaula de latón",
// "Juego interno C3"). No se explica que significa cada letra ni que otras
// opciones existen.

export interface Nomenclatura {
  publicar: boolean;
  motivoNoPublicar?: string;
  categoria?: string;          // solo cuando el codigo corrige la categoria de la descripcion
  tipo?: string;
  datos: string[];
  llaveDeUnion: string;        // piezas con la misma llave son la misma (UCP205-16-J7 = UCP205-16)
  codigoParaMedidas?: string;  // codigo con el que se buscan medidas (52xx usa las de 32xx)
  codigoSchaeffler?: string;   // como lo escribe Schaeffler (H 3124.403 -> H3124X403)
  medidas?: { agujeroMm?: number; agujeroPulgadas?: string; exteriorMm?: number; anchoMm?: number };
}

import { IGNORAR_TODO_CODIGO_CON_DIAGONAL } from './configuracion.ts';

const mm = (n: number) => `${Number(n.toFixed(3))} mm`;

// ---------- Chumaceras ----------

const TIPOS_CHUMACERA: Record<string, string> = {
  P: 'Chumacera de pedestal',
  F: 'Chumacera de brida cuadrada',
  FL: 'Chumacera de brida ovalada',
  T: 'Chumacera tensora',
  FC: 'Chumacera de brida cuadrada corta',
  PA: 'Chumacera de pedestal UCPA',
  FB: 'Chumacera de brida UCFB',
  FA: 'Chumacera de brida UCFA',
  HA: 'Chumacera colgante UCHA',
  // Variantes SNR con E: mismo tipo de caja
  PE: 'Chumacera de pedestal',
  FE: 'Chumacera de brida cuadrada',
  FLE: 'Chumacera de brida ovalada',
  FCE: 'Chumacera de brida cuadrada corta',
};
const CHUMACERA_ELIMINADA = new Set(['C', 'CP', 'PH']); // UCC y UCPH se eliminaron

const RE_CHUMACERA = /^(SS)?(UC|UK)([A-Z]*?)(\d{2,3})(?:-(\d{1,2}))?(.*)$/;

// Agujero en pulgadas: el numero despues del guion son dieciseisavos.
// 216-50 -> 50/16 = 3 1/8" = 79.375 mm.
export function agujeroChumacera(dieciseisavos: number): { pulgadas: string; mm: number } {
  const enteras = Math.floor(dieciseisavos / 16);
  let num = dieciseisavos % 16, den = 16;
  while (num && num % 2 === 0) { num /= 2; den /= 2; }
  const fraccion = num ? `${num}/${den}` : '';
  const pulgadas = [enteras || '', fraccion].filter(Boolean).join(' ') + '"';
  return { pulgadas, mm: Number((dieciseisavos / 16 * 25.4).toFixed(3)) };
}

// Codigo de diametro metrico: 00=10, 01=12, 02=15, 03=17, 04 en adelante x5.
function agujeroMetrico(codigo: number): number {
  return ([10, 12, 15, 17] as number[])[codigo] ?? codigo * 5;
}

function chumacera(np: string): Nomenclatura | null {
  const m = RE_CHUMACERA.exec(np);
  if (!m) return null;
  const [, ss, familia, letras, numero, pulgadas, resto] = m;
  const j7 = /^-?J7$/.test(resto);
  const llaveDeUnion = j7 ? np.replace(/-?J7$/, '') : np;

  let caja = letras;
  let reforzada = false, termoplastica = false;
  if (caja.endsWith('X')) { reforzada = true; caja = caja.slice(0, -1); }
  if (caja.length > 1 && caja.endsWith('P') && caja.slice(0, -1) in TIPOS_CHUMACERA) { termoplastica = true; caja = caja.slice(0, -1); }
  if (caja.endsWith('X')) { reforzada = true; caja = caja.slice(0, -1); }

  const base: Nomenclatura = { publicar: true, categoria: 'CHUMACERA', datos: [], llaveDeUnion };
  if (familia === 'UC' && CHUMACERA_ELIMINADA.has(letras)) {
    return { ...base, publicar: false, motivoNoPublicar: 'UCC y UCPH se eliminaron del catálogo' };
  }

  base.tipo = caja === '' ? 'Rodamiento de inserto para chumacera'
    : TIPOS_CHUMACERA[caja] ?? 'Chumacera';
  if (ss) base.datos.push('Acero inoxidable');
  if (termoplastica) base.datos.push('Caja termoplástica');
  if (reforzada) base.datos.push('Versión reforzada');

  const cod = Number(numero.slice(-2));
  if (familia === 'UK') {
    const manguito = /H23\d{2}/.exec(resto)?.[0] ?? `H23${numero.slice(-2)}`;
    base.datos.push('Agujero cónico');
    base.datos.push(/H23\d{2}/.test(resto) ? `Se monta con manguito ${manguito}` : `Se monta con manguito ${manguito} (se vende aparte)`);
  } else if (pulgadas) {
    const a = agujeroChumacera(Number(pulgadas));
    base.medidas = { agujeroMm: a.mm, agujeroPulgadas: a.pulgadas };
    base.datos.push(`Agujero de ${a.pulgadas} (${mm(a.mm)})`);
  } else {
    const a = agujeroMetrico(cod);
    base.medidas = { agujeroMm: a };
    base.datos.push(`Agujero de ${mm(a)}`);
  }
  return base;
}

// ---------- Manguitos ----------

// H, HA, HE, HS + serie. FAG con punto (H 2309.107) es otra pieza: DIBSA lo
// escribe sin punto (H2309107) o con X (H2328X500).
const RE_MANGUITO = /^(H|HA|HE|HS)\s?(\d{3,4})(?:[.X]?(\d{3}))?$/;

function manguito(np: string, marca: string): Nomenclatura | null {
  const limpio = np.replace(/\s/g, '');
  if (/^HM\d{2,4}T?$/.test(limpio) && marca !== 'TIMKEN') {
    return { publicar: false, motivoNoPublicar: 'Tuerca de bloqueo HM (excluida)', datos: [], llaveDeUnion: np };
  }
  const m = RE_MANGUITO.exec(limpio);
  if (!m || marca === 'TIMKEN') return null;
  const [, tipo, serie, pulgadas] = m;
  const n: Nomenclatura = {
    publicar: true, categoria: 'ACCESORIO', tipo: 'Manguito de fijación', datos: [], llaveDeUnion: np,
  };
  if (pulgadas) {
    n.codigoSchaeffler = `${tipo}${serie}X${pulgadas}`;
    n.datos.push('Agujero en pulgadas');
  }
  return n;
}

// Medidas de manguitos en pulgadas (Schaeffler): x 25.4 y redondeo a 0.5 mm.
export function manguitoPulgadasAMm(pulgadas: number): number {
  return Math.round(pulgadas * 25.4 * 2) / 2;
}

// ---------- Rodamientos ----------

// Casquillos de agujas HK/BK: diametro interior -> exterior (mm).
export const EXTERIOR_HK_BK: Record<number, number> = {
  3: 6, 4: 8, 5: 9, 6: 10, 8: 12, 10: 14, 12: 18, 14: 20, 15: 21, 16: 22, 18: 24,
  20: 26, 22: 28, 25: 32, 28: 35, 30: 37, 35: 42, 40: 47, 45: 52, 50: 58, 55: 63, 60: 68,
};

// Despues de la serie viene una letra, el fin, o "2" + letra (62052RS = 6205 + 2RS).
const FIN = '(?=$|[A-Z]|2[A-Z])';
const porSerie = (serie: string, nombre: string): [RegExp, string] => [new RegExp(`^(${serie})\\d{2}${FIN}`), nombre];
// Primero las series de 3 cifras, para que 22322 no se lea como 2232 + 2.
const TIPOS_RODAMIENTO: [RegExp, string][] = [
  porSerie('213|222|223|230|231|232|233|238|239|240|241|248|249', 'Rodamiento de rodillos esféricos'),
  porSerie('302|303|313|320|322|323|329|330|331|332', 'Rodamiento de rodillos cónicos'),
  porSerie('511|512|513|514', 'Rodamiento axial de bolas'),
  porSerie('292|293|294', 'Rodamiento axial de rodillos esféricos'),
  porSerie('811|812|893|874|894', 'Rodamiento axial de rodillos cilíndricos'),
  porSerie('160|161|618|619', 'Rodamiento rígido de bolas'),
  porSerie('60|62|63|64|16', 'Rodamiento rígido de bolas'),
  porSerie('12|13|22|23', 'Rodamiento de bolas autoalineable'),
  porSerie('72|73', 'Rodamiento de bolas de contacto angular'),
  porSerie('32|33|52|53', 'Rodamiento de bolas de contacto angular de dos hileras'),
  [/^(NN|NNU)\d{4}/, 'Rodamiento de rodillos cilíndricos de dos hileras'],
  [/^(NUP|NU|NJ|NF|N)\d{3,4}/, 'Rodamiento de rodillos cilíndricos'],
  [/^HK\d{4}/, 'Casquillo de agujas'],
  [/^BK\d{4}/, 'Casquillo de agujas con fondo cerrado'],
  [/^(NKIS|NKI|NA|NK|RNA)\d+/, 'Rodamiento de agujas'],
];
// Series donde la K final significa agujero conico.
const SERIE_CON_K = /^(12|13|22|23|213|222|223|230|231|232|233|238|239|240|241|248|249)\d{2}/;

// Familias que no siguen la serie ISO de 2 o 3 cifras. Se revisan despues de
// TIPOS_RODAMIENTO. "sufijos" indica si las letras finales se leen con SUFIJOS
// (solo en rodamientos de norma; en seguidores, rotulas o lineales las letras
// significan otra cosa). "marcas" limita la regla a esas marcas.
interface Regla { re: RegExp; tipo: string; sufijos?: boolean; marcas?: string[]; sinMarcas?: string[] }
const BOLAS = 'Rodamiento rígido de bolas';
const CONTACTO_ANGULAR = 'Rodamiento de bolas de contacto angular';
const INSERTO = 'Rodamiento de inserto para chumacera';
const SEGUIDOR_PERNO = 'Seguidor de leva con perno';
const SEGUIDOR_YUGO = 'Rodillo seguidor tipo yugo';
const PISTA_AGUJAS = 'Pista interior para rodamiento de agujas';
const JUEGO_CONO_TAZA = 'Juego de cono y taza';
const regla = ([re, tipo]: [RegExp, string], extra: Partial<Regla> = {}): Regla => ({ re, tipo, ...extra });
const conSufijos = (serie: string, nombre: string, extra: Partial<Regla> = {}) => regla(porSerie(serie, nombre), { sufijos: true, ...extra });

// Insertos: tambien valen para Timken (G1110KRR, RA100RR, W208PP).
const REGLAS_INSERTO: Regla[] = [
  { re: /^GN?E\d{2,5}(XL)?K(RR|LL)/, tipo: INSERTO },        // GE25KRRB, GE30XLKRRB
  { re: /^(GAY|GRAE|RAE|RALE)\d/, tipo: INSERTO },
  { re: /^RA\d{2,3}(NPP|RR)/, tipo: INSERTO },                // RA106NPPB, RA012RR
  { re: /^G1\d{3}KR/, tipo: INSERTO },                        // G1110KRR
  { re: /^W\d{3}PP/, tipo: INSERTO },                         // W208PP
  { re: /^SA2\d{2}/, tipo: INSERTO },                         // SA202 (collar excentrico)
];
// Rotulas. GE + medida + E/ES/ESX es rotula radial (GE10E), no inserto.
const RE_ROTULA_RADIAL = /^GE[GZ]?\d{1,3}E/;
const RE_TERMINAL = /^(PHSB|POSB|PHS|POS|GAR|GIR|GAL|GAKR|GIKR)\d/;
const REGLAS_ROTULA: Regla[] = [
  { re: RE_ROTULA_RADIAL, tipo: 'Rótula radial' },
  { re: RE_TERMINAL, tipo: 'Terminal de rótula' },
  { re: /^(SI|SA)L?\d{1,2}[A-Z]/, tipo: 'Terminal de rótula' }, // SA10E, SAL15ES2RS, SI35C2RS; SA202/SA205 (sin letra) son insertos
];

const TIPOS_RODAMIENTO_2: Regla[] = [
  // Rigido de bolas: series de 3 cifras y miniatura (608, 688, 6800, 69052RS)
  conSufijos('617|622|623|630|637|638', BOLAS),
  regla([/^(68|69)[0-3]\d(?=$|[A-Z]|2[A-Z])/, BOLAS], { sufijos: true }),
  regla([/^6\d[1-9](?=$|[A-Z]|2[A-Z])/, BOLAS], { sufijos: true }),
  regla([/^R(1810|1[3-8][3-8]|\d{1,2}?)(?=$|[A-Z]|2[A-Z])/, BOLAS], { sufijos: true }), // pulgadas: R6-2Z, R12, R1682Z
  regla([/^MR\d{2,3}?(?=$|[A-Z]|2[A-Z])/, BOLAS], { sufijos: true, sinMarcas: ['MC GILL', 'LINK BELT'] }),
  regla([/^MR\d/, 'Rodamiento de agujas'], { marcas: ['MC GILL'] }),
  conSufijos('42|43', 'Rodamiento rígido de bolas de dos hileras'),
  // Contacto angular
  conSufijos('718|719', CONTACTO_ANGULAR),
  conSufijos('70|74', CONTACTO_ANGULAR),
  regla([/^(B|HCB|HCS|HSS|HC)(70|72|718|719)\d{2}(?=$|[A-Z]|2[A-Z])/, CONTACTO_ANGULAR], { sufijos: true }), // husillo FAG
  regla([/^[23]MMC?\d{3,4}/, CONTACTO_ANGULAR], { marcas: ['FAFNIR'] }),
  conSufijos('38', 'Rodamiento de bolas de contacto angular de dos hileras'),
  regla([/^QJ(2|3|10|12)\d{2}(?=$|[A-Z]|2[A-Z])/, 'Rodamiento de bolas de contacto de cuatro puntos'], { sufijos: true }),
  conSufijos('112', 'Rodamiento de bolas autoalineable'),
  // Axiales (52209 es axial; 5209 de 4 cifras sigue siendo contacto angular de dos hileras)
  conSufijos('522|523|524|532|533|534', 'Rodamiento axial de bolas'),
  regla([/^234[47]\d{2}(?=$|[A-Z])/, 'Rodamiento axial de bolas de contacto angular'], { sufijos: true }),
  regla([/^K(811|812|893|874|894)\d{2}/, 'Corona axial de rodillos']),
  regla([/^AXK\d/, 'Corona axial de agujas']),
  regla([/^(AS\d{4}|LS\d{4}|GS8\d{4}|WS8\d{4})/, 'Arandela axial']),
  // Agujas
  regla([/^(NKXR?|NKIB)\d/, 'Rodamiento de agujas combinado']),
  regla([/^(NKS|NAO|RNAO)\d/, 'Rodamiento de agujas']),
  regla([/^ZAR[NF]\d/, 'Rodamiento combinado de agujas y rodillos axiales']),
  regla([/^ZKL[FN]A?\d/, 'Rodamiento axial de bolas de contacto angular para husillo']),
  regla([/^K\d+X\d+X\d/, 'Corona de agujas']),
  regla([/^NRB\d/, 'Agujas sueltas']),
  regla([/^SCE\d/, 'Casquillo de agujas']),
  regla([/^BCE\d/, 'Casquillo de agujas con fondo cerrado']),
  // Cilindricos de llenado completo INA
  regla([/^SL(0[145]|18|19)\d{3,4}/, 'Rodamiento de rodillos cilíndricos de llenado completo'], { sufijos: true }),
  // Esfericos McGill (SB22208W33SS)
  regla([/^SB22[23]\d{2}/, 'Rodamiento de rodillos esféricos'], { marcas: ['MC GILL'] }),
  // Seguidores y rodillos de apoyo
  regla([/^(CCFH|CCF|CFH|CF|MCFR|MCF|NUKR|PWKR)\d/, SEGUIDOR_PERNO]),
  regla([/^KRV?\d{2}(?!\d)/, SEGUIDOR_PERNO]),
  regla([/^(CCYR|CYR|MCYRR?|NATR|NATV|NUTR|RSTO|STO)\d/, SEGUIDOR_YUGO]),
  regla([/^LR\d+X\d+X\d/, PISTA_AGUJAS]),                   // LR20X25X125: anillo interior
  regla([/^LR\d{3,5}/, 'Rodillo de apoyo']),
  regla([/^MI\d/, PISTA_AGUJAS], { marcas: ['MC GILL', 'SMITH'] }),
  ...REGLAS_INSERTO,
  { re: RE_ROTULA_RADIAL, tipo: 'Rótula radial' },
  { re: RE_TERMINAL, tipo: 'Terminal de rótula' },
  regla([/^713\d{6}$/, 'Maza de rueda'], { marcas: ['FAG'] }),
  regla([/^(KWVE|KWSE|KWE|RWU)\d/, 'Carro de guía lineal']),
  regla([/^SET\d/, JUEGO_CONO_TAZA]),
];
const REGLAS_TIMKEN: Regla[] = [...REGLAS_INSERTO, regla([/^SET\d/, JUEGO_CONO_TAZA])];
// Juegos de cono y taza con K (FERSA, ISB, PFI): KLM11749/10, KHM88542/88510, K02474/20.
const RE_JUEGO_K = /^K[A-Z]{0,3}\d{3,6}[A-Z]{0,2}\//;

// Cuando el codigo no decide, decide la descripcion de DIBSA.
const TIPOS_POR_DESCRIPCION: [RegExp, string][] = [
  [/\b(CONO Y TAZA|TAZA Y CONO)\b/, JUEGO_CONO_TAZA],
  [/\bCONO\b/, 'Cono de rodamiento de rodillos cónicos'],
  [/\bTAZA\b/, 'Taza de rodamiento de rodillos cónicos'],
  [/\bMAZA\b/, 'Maza de rueda'],
  [/\bCASQUILLO DE AGUJAS\b/, 'Casquillo de agujas'],
  [/\bDISCO AXIAL\b/, 'Arandela axial'],
  [/\bCARR(O|ITO) LINEAL\b/, 'Carro de guía lineal'],
  [/\bGUIA LINEAL\b/, 'Guía lineal'],
];

const TIPOS_DE_DESCRIPCION_PRIMERO = new Set(
  TIPOS_POR_DESCRIPCION.filter(([re]) => /CONO|TAZA|MAZA/.test(re.source)).map(([, t]) => t));

function buscarRegla(c: string, marca: string, reglas: Regla[]): { regla: Regla; largo: number } | null {
  for (const r of reglas) {
    if (r.marcas && !r.marcas.includes(marca)) continue;
    if (r.sinMarcas?.includes(marca)) continue;
    const m = r.re.exec(c);
    if (m) return { regla: r, largo: m[0].length };
  }
  return null;
}
const tipoPorDescripcion = (descripcion: string) =>
  TIPOS_POR_DESCRIPCION.find(([re]) => re.test(descripcion.toUpperCase()))?.[1];

// Sufijos, del mas largo al mas corto. Cada uno da UN dato de la pieza.
const SUFIJOS: [RegExp, string | null][] = [
  [/^FT150/, 'Para temperatura de hasta 150 °C'],
  [/^HT200/, 'Para temperatura de hasta 200 °C'],
  [/^F60[04]/, 'Para temperatura de hasta 300 °C'],
  [/^(2RSR|2RS1|2RSH|2RSL|2RS|LLU|DDU|2HRS)/, 'Sellos de hule en ambos lados'],
  [/^(2RZ|LLB)/, 'Sellos de hule sin contacto en ambos lados'],
  [/^(2ZR|2Z|ZZ)/, 'Tapas metálicas en ambos lados'],
  [/^(RSR|RS1|RSH|RS)/, 'Sello de hule en un lado'],
  [/^ZNR/, 'Tapa metálica en un lado, con ranura y anillo de retención'],
  [/^NR/, 'Con ranura y anillo de retención'],
  [/^(ECP|TVP2|TVPB|TVP|TVH|TN9|TNH|TN)/, 'Jaula de poliamida'],
  [/^MAX/, null],     // ISB 38022RSVMAX: no es jaula de latón
  [/^(ECM|M1A|M1B|MPA|MPB|M1|MA|MB|MP|M)/, 'Jaula de latón'],
  [/^J\d+/, null],   // SNR 7005CVDUJ74, 4308J30: J + numero no es jaula de acero
  [/^(ECJ|JPA|JP3|JP|JN|J(?!\d))/, 'Jaula de acero'],
  [/^T41[AD]/, 'Para cribas vibratorias'],
  [/^(EW33|W33)/, 'Ranura y orificios de lubricación en el aro exterior'],
  [/^C(?=2(HRS|RSR|RS|Z|BRS|RZ))/, null], // FAG generacion C antes del sello (6000C2HRSL038C3)
  [/^L0\d\d/, null],                       // codigo de grasa (L038)
  [/^C([2-5])/, 'Juego interno C$1'],
  [/^P([2456])/, 'Precisión P$1'],
  [/^(E1|EA|EC|E|XL|A|B|CC|CA)/, null], // diseño interno: no se lista en la ficha
];

// "60/22": serie + diametro interior en mm despues de la diagonal.
const RE_SERIE_DIAMETRO = /^(60|62|63|64|160|161|618|619|302|303|320|322|323|329|330|331|332|222|223|230|231|232|238|239|240|241|248|249|NUP|NU|NJ|NNU|NN|N)\/\d/;

function rodamiento(np: string, marca: string, descripcion = ''): Nomenclatura {
  const n: Nomenclatura = { publicar: true, datos: [], llaveDeUnion: np };
  let c = np.toUpperCase().replace(/[\s-]/g, '');

  const diagonal = IGNORAR_TODO_CODIGO_CON_DIAGONAL ? c.includes('/') : RE_SERIE_DIAMETRO.test(c);
  if (diagonal) return { ...n, publicar: false, motivoNoPublicar: 'Código con "/" (se ignora)' };
  if (/^54\d{3}(?!\d)/.test(c) && marca !== 'TIMKEN') return { ...n, publicar: false, motivoNoPublicar: 'Serie 54 sin existencia' };
  if (/^HC\s?719/.test(c)) return { ...n, publicar: false, motivoNoPublicar: 'HC 719 (excluido)' };
  if (marca === 'TIMKEN') { // numeros en pulgadas de Timken: sin reglas de sufijo
    n.tipo = buscarRegla(c, marca, REGLAS_TIMKEN)?.regla.tipo ?? tipoPorDescripcion(descripcion);
    return n;
  }
  // Conos, tazas y mazas: manda la descripcion (FERSA 665 'CONO' no es de bolas).
  const porDescripcion = tipoPorDescripcion(descripcion);
  if (porDescripcion && TIPOS_DE_DESCRIPCION_PRIMERO.has(porDescripcion)) return { ...n, tipo: porDescripcion };
  const juegoK = RE_JUEGO_K.test(c);

  // SS-63052RS: acero inoxidable. F6072Z: con brida (FERSA F19119 no es de bolas).
  let inoxidable = false, conBrida = false;
  if (/^SS-/.test(np.toUpperCase()) && !c.includes('/')) { inoxidable = true; c = c.slice(2); }
  if (/^F6/.test(c) && marca !== 'FERSA') { conBrida = true; c = c.slice(1); }

  if (/^5[23]\d{2}(?!\d)/.test(c)) n.codigoParaMedidas = c.replace(/^5([23])/, '3$1');

  c = c.replace(/\//g, ''); // 22206CCC3/W33: la diagonal solo separa sufijos
  let resto = c;
  // Miniatura de 3 cifras + sello doble: 6082RS = 608-2RS (no 6082-RS).
  const mini = /^(60[4-9]|62[3-9]|63[3-9]|68[1-9]|69[1-9])(?=2(RS|Z|RZ|HRS))/.exec(c);
  if (mini) { n.tipo = 'Rodamiento rígido de bolas'; resto = c.slice(3); }
  else for (const [re, tipo] of TIPOS_RODAMIENTO) {
    const m = re.exec(c);
    if (!m) continue;
    // 32032RSE = 3203 + 2RS (contacto angular de dos hileras), no 320 + 32 + RS.
    if (tipo === 'Rodamiento de rodillos cónicos' && /^\d{5}$/.test(m[0]) && m[0].endsWith('2') && /^(RSR|RS|Z|RZ|HRS)/.test(c.slice(5))) continue;
    n.tipo = tipo; resto = c.slice(m[0].length);
    // NA22/62RSR -> NA2262RSR: el 2 final es del sello doble (2RSR), no de la medida.
    if (tipo === 'Rodamiento de agujas' && m[0].endsWith('2') && /^(RSR|RS|Z|RZ|HRS)/.test(resto)) resto = '2' + resto;
    break;
  }
  let sufijos = true, reglaNueva = false;
  if (!n.tipo) {
    const r = buscarRegla(c, marca, TIPOS_RODAMIENTO_2);
    if (r) { n.tipo = r.regla.tipo; resto = c.slice(r.largo); sufijos = !!r.regla.sufijos; reglaNueva = true; }
  }
  if ((inoxidable || conBrida) && n.tipo !== BOLAS) return { ...n, tipo: undefined };
  if (conBrida) n.tipo = 'Rodamiento rígido de bolas con brida';
  if (inoxidable) n.datos.push('Acero inoxidable');
  if (!n.tipo) { n.tipo = juegoK ? JUEGO_CONO_TAZA : tipoPorDescripcion(descripcion); sufijos = false; }
  if (!n.tipo || !sufijos) return n;
  if (reglaNueva) resto = resto.replace(/^C(?=2(Z|HRS|RS))/, ''); // FAG 629-C-2Z: la C es diseño, no juego C2
  if (reglaNueva && /^SL/.test(c)) resto = resto.replace(/^PP(2|Z)?/, ''); // SL...PP2NR: PP2/PPZ son sello y diseño, no P2 ni ZNR
  // NSK 607DDMC3E / 6282ZMC3E: MC3 tras el sello es un solo codigo, no jaula de latón ni juego C3.
  // (22322E1AMC3 de FAG si es M + C3: solo se quita cuando va pegado a un sello.)
  resto = resto.replace(/(?<=DD|ZZ|VV|Z|RS)MC[1-6]/, '');
  // Husillo FAG: UM/DUM/SUM al final es disposicion universal + precarga, no jaula de latón.
  if (reglaNueva && /^(B|HCB|HCS|HSS|HC)(70|72|718|719)/.test(c)) resto = resto.replace(/(S?D?U[LMHA]|D[BFT])$/, '');

  const hk = /^(HK|BK)(\d{2})(\d{2})/.exec(c);
  if (hk) {
    const d = Number(hk[2]), b = Number(hk[3]);
    n.medidas = { agujeroMm: d, exteriorMm: EXTERIOR_HK_BK[d], anchoMm: b };
  }
  const conK = SERIE_CON_K.test(c);

  const vistos = new Set<string>();
  let i = 0;
  while (i < resto.length) {
    const trozo = resto.slice(i);
    let avance = 1;
    if (conK && trozo.startsWith('K')) {
      if (!vistos.has('K')) { vistos.add('K'); n.datos.push('Agujero cónico'); }
      i++; continue;
    }
    for (const [re, dato] of SUFIJOS) {
      const m = re.exec(trozo);
      if (!m) continue;
      avance = m[0].length;
      if (dato) {
        const texto = m[0].replace(re, dato);
        if (!vistos.has(texto)) { vistos.add(texto); n.datos.push(texto); }
      }
      break;
    }
    i += avance;
  }
  return n;
}

// ---------- Cadenas ----------

function cadena(np: string): Nomenclatura | null {
  const c = np.toUpperCase();
  if (!c.startsWith('CADENA')) return null;
  const n: Nomenclatura = { publicar: true, categoria: 'CADENA', tipo: 'Cadena', datos: [], llaveDeUnion: np };
  const hileras = /^CADENA\d{2,3}-(\d)/.exec(c)?.[1] ?? /^CADENA\d{2}-B(\d)/.exec(c)?.[1];
  const nombres: Record<string, string> = { '1': 'Sencilla', '2': 'Doble hilera', '3': 'Triple hilera', '4': 'Cuádruple hilera' };
  if (hileras && nombres[hileras]) n.datos.push(nombres[hileras]);
  if (/SS/.test(c.slice(6))) n.datos.push('Acero inoxidable');
  const metros = /\((\d+(?:\.\d+)?)\s?MTS?\)/.exec(c)?.[1];
  n.datos.push(metros ? `Caja de ${metros} m` : 'Caja de 3.05 m');
  return n;
}

// ---------- Entrada principal ----------

export function leerNomenclatura(numeroDeParte: string, marca: string, categoria: string, descripcion = ''): Nomenclatura {
  const np = numeroDeParte.trim().toUpperCase();
  if (/^TSNG/.test(np)) {
    return { publicar: true, categoria: 'ACCESORIO', tipo: 'Sello de laberinto de hule para soporte SNL', datos: [], llaveDeUnion: np };
  }
  if (/^SNL/.test(np)) {
    return {
      publicar: true, categoria: 'CHUMACERA', tipo: 'Soporte de pie bipartido',
      datos: ['Solo la caja bipartida: no incluye rodamiento, buje ni sello'], llaveDeUnion: np,
    };
  }
  if (/^BALAS/.test(np)) return { publicar: true, tipo: 'Balas (esferas) sueltas', datos: [], llaveDeUnion: np };
  const ch = chumacera(np); if (ch) return ch;
  const mg = manguito(np, marca); if (mg) return mg;
  const cd = cadena(np); if (cd) return cd;
  if (categoria === 'ROTULA') {
    return { publicar: true, tipo: buscarRegla(np.replace(/[\s-]/g, ''), marca, REGLAS_ROTULA)?.regla.tipo, datos: [], llaveDeUnion: np };
  }
  if (categoria === 'RODAMIENTO' || (categoria === 'OTROS' && /^[A-Z]{0,4}\d/.test(np) && !/BANDA|POLEA|CATARINA/.test(descripcion))) {
    return rodamiento(np, marca, descripcion);
  }
  return { publicar: true, datos: [], llaveDeUnion: np };
}
