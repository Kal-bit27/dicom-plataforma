import {
  CATEGORIAS_MARTIN_PERMITIDAS, HORAS_SINCRONIZACION, MARCAS_INVENTARIO_PROPIO,
  MARCAS_SOLO_CONSULTA, SUCURSALES, SUCURSAL_LOCAL,
} from './configuracion.ts';
import { esDiaHabil, horaLocal } from './entrega.ts';
import { leerNomenclatura, type Nomenclatura } from './nomenclatura.ts';
import { normalizarMarca } from './precios.ts';

// Lector de CSV con comillas (el archivo de DIBSA trae comas dentro de comillas).
export function leerCsv(texto: string): Record<string, string>[] {
  const filas: string[][] = [];
  let fila: string[] = [], campo = '', enComillas = false;
  const t = texto.charCodeAt(0) === 0xfeff ? texto.slice(1) : texto;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (enComillas) {
      if (c === '"' && t[i + 1] === '"') { campo += '"'; i++; }
      else if (c === '"') enComillas = false;
      else campo += c;
    } else if (c === '"') enComillas = true;
    else if (c === ',') { fila.push(campo); campo = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && t[i + 1] === '\n') i++;
      fila.push(campo); campo = '';
      if (fila.length > 1 || fila[0] !== '') filas.push(fila);
      fila = [];
    } else campo += c;
  }
  if (campo !== '' || fila.length) { fila.push(campo); filas.push(fila); }
  const [encabezado, ...resto] = filas;
  if (!encabezado) return [];
  return resto.map((f) => Object.fromEntries(encabezado.map((h, i) => [h.trim(), f[i] ?? ''])));
}

// Clave de busqueda: "6205-2RS", "6205 2rs" y "62052RS" dan lo mismo.
export function claveDeBusqueda(numeroDeParte: string): string {
  return numeroDeParte.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

const REGLAS_CATEGORIA: [RegExp, string][] = [
  [/\bCHUMACERA|\bSOPORTE|\bBLOCK\b/, 'CHUMACERA'],
  [/\bRETEN|\bSELLO\b/, 'RETEN'],
  [/\bBANDA|\bOPTIBELT|\bJASON\b|\bGOODYEAR\b/, 'BANDA'],
  [/\bCADENA|\bCANDADO|\bMEDIO\b/, 'CADENA'],
  [/\bCATARINA|\bSPROCKET/, 'CATARINA'],
  [/\bPOLEA/, 'POLEA'],
  [/\bBUJE/, 'BUJE'],
  [/\bCOPLE/, 'COPLE'],
  [/\bROTULA/, 'ROTULA'],
  [/\bGRASA|\bLUBRICANTE/, 'LUBRICANTE'],
  [/\bROD(AMIENTOS?|AMEINTO|MAIENTO|\.)?\b|\bCONO\b|\bTAZA\b|\bSEGUIDOR|\bAGUJAS|\bRODILLO|\bMAZA\b/, 'RODAMIENTO'],
  [/\bCASQUILLO|\bMANGUITO|\bTUERCA|\bARANDELA|\bANILLO|\bSEGURO\b/, 'ACCESORIO'],
];

export function categoriaDe(descripcion: string): string {
  const d = descripcion.toUpperCase();
  for (const [patron, categoria] of REGLAS_CATEGORIA) if (patron.test(d)) return categoria;
  return 'OTROS';
}

export interface ProductoDibsa {
  numeroDeParte: string;
  clave: string;
  marca: string;
  descripcion: string;
  categoria: string;
  precioDibsa: number;
  existencias: Record<string, number>;   // por sucursal
  existenciaLocal: number;               // DIBSA CDMX
  existenciaTotal: number;               // suma de sucursales
  existenciaDesdeInventarioPropio: boolean;
  soloConsulta: boolean;
  publicar: boolean;
  motivoNoPublicar?: string;
  renglonesUnidos: number;               // >1 cuando DIBSA repite el producto
  otrosNombres: string[];                // p. ej. UCP205-16-J7 unido a UCP205-16; tambien se encuentra al buscar
  tipo?: string;                         // "Chumacera de pedestal", "Rodamiento rígido de bolas"...
  datos: string[];                       // datos de la pieza para la ficha (solo los que aplican)
  medidas?: Nomenclatura['medidas'];
  codigoParaMedidas?: string;            // 52xx/53xx usan las medidas de 32xx/33xx
  codigoSchaeffler?: string;             // H 3124.403 -> H3124X403
}

export interface ResultadoImportacion {
  productos: ProductoDibsa[];
  renglonesLeidos: number;
  descartados: { renglon: number; motivo: string }[];
  repetidosUnidos: number;
}

const entero = (v: string) => { const n = Math.trunc(Number(v)); return Number.isFinite(n) && n > 0 ? n : 0; };

export function importarDibsa(textoCsv: string): ResultadoImportacion {
  const filas = leerCsv(textoCsv);
  const porLlave = new Map<string, ProductoDibsa>();
  const descartados: ResultadoImportacion['descartados'] = [];
  let repetidosUnidos = 0;

  filas.forEach((f, i) => {
    const numeroDeParte = (f.ID_PRODUCTO ?? '').trim();
    const marca = normalizarMarca(f.MARCA ?? '');
    const precioDibsa = Number(f.PRECIO_UNITARIO);
    if (!numeroDeParte || !marca) return void descartados.push({ renglon: i + 2, motivo: 'Sin numero de parte o marca' });
    if (!(precioDibsa > 0)) return void descartados.push({ renglon: i + 2, motivo: 'Precio no valido' });

    const existencias: Record<string, number> = {};
    for (const s of SUCURSALES) existencias[s] = entero(f[s] ?? '0');
    const descripcion = (f.DESCRIPCION ?? '').trim();
    const nom = leerNomenclatura(numeroDeParte, marca, categoriaDe(descripcion), descripcion);
    // Se une por numero de parte exacto ("62/28" y "6228" son piezas distintas),
    // salvo las chumaceras J7, que son la misma pieza que la version con guion.
    const llave = `${marca}|${nom.llaveDeUnion.toUpperCase()}`;
    const previo = porLlave.get(llave);

    if (previo) {
      // DIBSA repite algunos productos con existencias distintas. Se toma, por
      // sucursal, la cifra mayor (nunca la suma, para no prometer de mas).
      repetidosUnidos++;
      previo.renglonesUnidos++;
      for (const s of SUCURSALES) previo.existencias[s] = Math.max(previo.existencias[s], existencias[s]);
      if (descripcion.length > previo.descripcion.length) previo.descripcion = descripcion;
      previo.precioDibsa = Math.max(previo.precioDibsa, precioDibsa);
      if (numeroDeParte.toUpperCase() !== previo.numeroDeParte.toUpperCase()) {
        // Se publica con el nombre sin J7; el otro queda como nombre alterno.
        const sinJ7 = numeroDeParte.toUpperCase() === nom.llaveDeUnion.toUpperCase();
        const alterno = sinJ7 ? previo.numeroDeParte : numeroDeParte;
        if (sinJ7) { previo.numeroDeParte = numeroDeParte; previo.clave = claveDeBusqueda(numeroDeParte); }
        if (!previo.otrosNombres.includes(alterno)) previo.otrosNombres.push(alterno);
      }
      return;
    }
    porLlave.set(llave, {
      numeroDeParte, clave: claveDeBusqueda(numeroDeParte), marca, descripcion,
      precioDibsa, existencias,
      existenciaLocal: 0, existenciaTotal: 0,
      existenciaDesdeInventarioPropio: MARCAS_INVENTARIO_PROPIO.has(marca),
      soloConsulta: MARCAS_SOLO_CONSULTA.has(marca),
      publicar: nom.publicar, motivoNoPublicar: nom.motivoNoPublicar, renglonesUnidos: 1,
      otrosNombres: [], tipo: nom.tipo, datos: nom.datos, medidas: nom.medidas,
      codigoParaMedidas: nom.codigoParaMedidas, codigoSchaeffler: nom.codigoSchaeffler,
      categoria: nom.categoria ?? '',
    });
  });

  const productos = [...porLlave.values()];
  for (const p of productos) {
    p.categoria ||= categoriaDe(p.descripcion);
    p.existenciaLocal = p.existencias[SUCURSAL_LOCAL];
    p.existenciaTotal = SUCURSALES.reduce((a, s) => a + p.existencias[s], 0);
    if (p.soloConsulta && p.publicar && !CATEGORIAS_MARTIN_PERMITIDAS.has(p.categoria)) {
      p.publicar = false; p.motivoNoPublicar = 'Martin: solo bujes, poleas y catarinas';
    }
  }
  return { productos, renglonesLeidos: filas.length, descartados, repetidosUnidos };
}

// La actualizacion solo corre de lunes a viernes a las horas configuradas
// (hora del centro de Mexico). Un programador la invoca cada hora y esta
// funcion decide si toca.
export function tocaSincronizar(ahora: Date, horas = HORAS_SINCRONIZACION): boolean {
  const { dia, hora } = horaLocal(ahora);
  return esDiaHabil(dia) && horas.includes(hora);
}
