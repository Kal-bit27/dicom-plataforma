import {
  HORA_CORTE_ENVIO, MARCAS_SOLO_CONSULTA, PESO_MAXIMO_ENVIO_GRATIS_KG, ZONA_HORARIA,
} from './configuracion.ts';
import { normalizarMarca } from './precios.ts';

export type AvisoEntrega =
  | 'ENVIA_HOY'            // sale hoy mismo; el resto es tiempo de paqueteria
  | 'ENVIA_SIGUIENTE_DIA'  // hay en CDMX pero ya paso el corte o no es dia habil
  | 'MAYOR_TIEMPO'         // parte o todo viene de otra sucursal
  | 'CONSULTAR'            // se atiende por formulario (Martin)
  | 'SIN_EXISTENCIA';      // la cantidad pedida no se cubre ni sumando sucursales

export interface EntradaEntrega {
  marca: string;
  cantidad: number;
  existenciaLocal: number;   // DIBSA CDMX, o inventario propio en ISB
  existenciaTotal: number;   // suma de todas las sucursales
  ahora?: Date;
}

// Hora y dia de la semana en Mexico, sin depender de la zona del servidor.
export function horaLocal(fecha: Date, zona = ZONA_HORARIA) {
  const partes = new Intl.DateTimeFormat('en-US', {
    timeZone: zona, weekday: 'short', hour: 'numeric', minute: 'numeric', hourCycle: 'h23',
  }).formatToParts(fecha);
  const v = (t: string) => partes.find((p) => p.type === t)!.value;
  const dia = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(v('weekday'));
  return { dia, hora: Number(v('hour')), minuto: Number(v('minute')) };
}

export const esDiaHabil = (dia: number) => dia >= 1 && dia <= 5;

export function avisoDeEntrega(e: EntradaEntrega): AvisoEntrega {
  if (!Number.isInteger(e.cantidad) || e.cantidad < 1) throw new Error('Cantidad no valida');
  if (MARCAS_SOLO_CONSULTA.has(normalizarMarca(e.marca))) return 'CONSULTAR';
  if (e.cantidad > e.existenciaTotal) return 'SIN_EXISTENCIA';
  if (e.cantidad > e.existenciaLocal) return 'MAYOR_TIEMPO';
  const { dia, hora } = horaLocal(e.ahora ?? new Date());
  return esDiaHabil(dia) && hora < HORA_CORTE_ENVIO ? 'ENVIA_HOY' : 'ENVIA_SIGUIENTE_DIA';
}

export const TEXTO_AVISO: Record<AvisoEntrega, string> = {
  ENVIA_HOY: 'Entrega inmediata: se envía hoy mismo. El tiempo restante es el de la paquetería.',
  ENVIA_SIGUIENTE_DIA: 'Entrega inmediata: se envía el siguiente día hábil.',
  MAYOR_TIEMPO: 'Mayor tiempo de entrega: parte de este material viene de otra sucursal.',
  CONSULTAR: 'Consultar tiempo de entrega.',
  SIN_EXISTENCIA: 'No hay existencia suficiente para esa cantidad.',
};

export type AvisoEnvio = 'ENVIO_GRATIS' | 'ENVIO_A_COTIZAR' | 'PESO_POR_CONFIRMAR';

export function avisoDeEnvio(pesoKg: number | null | undefined): AvisoEnvio {
  if (pesoKg == null) return 'PESO_POR_CONFIRMAR';
  return pesoKg <= PESO_MAXIMO_ENVIO_GRATIS_KG ? 'ENVIO_GRATIS' : 'ENVIO_A_COTIZAR';
}
