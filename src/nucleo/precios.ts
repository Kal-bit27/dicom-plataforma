import {
  FACTORES_POR_MARCA, FACTOR_POR_DEFECTO, IVA, UTILIDAD_POR_DEFECTO,
} from './configuracion.ts';

export const redondear = (n: number): number => Math.round((n + Number.EPSILON) * 100) / 100;

export function normalizarMarca(marca: string): string {
  return marca.trim().toUpperCase().replace(/\s+/g, ' ');
}

export function factorDeMarca(marca: string, factores = FACTORES_POR_MARCA): number {
  return factores[normalizarMarca(marca)] ?? FACTOR_POR_DEFECTO;
}

export interface EntradaPrecio {
  precioDibsa: number;        // precio publicado por DIBSA, sin IVA
  marca: string;
  utilidad?: number;          // 0.20 = 20% sobre el costo
  envioEstimado?: number;     // costo de envio que se absorbe en el precio
  factor?: number;            // si el producto tiene un factor propio
}

export interface DesglosePrecio {
  factor: number;
  costo: number;              // lo que DICOM paga a DIBSA, sin IVA
  envioEstimado: number;
  precioVenta: number;        // precio al cliente, sin IVA
  iva: number;
  precioConIva: number;
  utilidadPesos: number;      // precioVenta - costo - envio
  utilidadPorcentaje: number; // sobre el precio de venta
}

export function calcularPrecio(e: EntradaPrecio): DesglosePrecio {
  if (!(e.precioDibsa > 0)) throw new Error('El precio de DIBSA debe ser mayor que cero');
  const factor = e.factor ?? factorDeMarca(e.marca);
  const utilidad = e.utilidad ?? UTILIDAD_POR_DEFECTO;
  const envioEstimado = e.envioEstimado ?? 0;
  if (utilidad < 0) throw new Error('La utilidad no puede ser negativa: se venderia bajo costo');
  const costo = redondear(e.precioDibsa * factor);
  const precioVenta = redondear(costo * (1 + utilidad) + envioEstimado);
  const iva = redondear(precioVenta * IVA);
  const utilidadPesos = redondear(precioVenta - costo - envioEstimado);
  return {
    factor, costo, envioEstimado, precioVenta, iva,
    precioConIva: redondear(precioVenta + iva),
    utilidadPesos,
    utilidadPorcentaje: redondear((utilidadPesos / precioVenta) * 100),
  };
}

export interface RenglonPedido { cantidad: number; precio: DesglosePrecio }

// Utilidad de un pedido completo. La comision del cobro se resta aqui porque
// se cobra sobre el total pagado (con IVA).
export function utilidadDePedido(renglones: RenglonPedido[], comisionCobro = 0) {
  let subtotal = 0, costo = 0, envio = 0;
  for (const r of renglones) {
    subtotal += r.precio.precioVenta * r.cantidad;
    costo += r.precio.costo * r.cantidad;
    envio += r.precio.envioEstimado * r.cantidad;
  }
  subtotal = redondear(subtotal);
  const iva = redondear(subtotal * IVA);
  const total = redondear(subtotal + iva);
  const comision = redondear(total * comisionCobro);
  return {
    subtotal, iva, total,
    costo: redondear(costo), envio: redondear(envio), comision,
    utilidad: redondear(subtotal - costo - envio - comision),
  };
}
