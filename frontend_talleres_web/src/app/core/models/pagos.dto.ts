export interface PagoDto {
  id: number;
  incidente_id: number;
  cliente_id: number;
  tecnico_id: number;
  monto_total: number;
  monto_taller: number;
  comision_plataforma: number;
  metodo_pago: string;
  estado: string;
  created_at: string | null;
}

export interface PagoListResponseDto {
  items: PagoDto[];
  total: number;
  page: number;
  page_size: number;
}

