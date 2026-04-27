/** 1=Lun … 7=Dom, alineado a los botones de la UI. */

export const DIA_CORTO = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'] as const;

const RE_ESTRUCT = /^D:([1-7](?:,[1-7])*)\|(\d{2}:\d{2})-(\d{2}:\d{2})$/;

export type HorarioStruct = {
  days: [boolean, boolean, boolean, boolean, boolean, boolean, boolean];
  inicio: string;
  fin: string;
};

export const defaultHorarioStruct = (): HorarioStruct => ({
  days: [true, true, true, true, true, false, false],
  inicio: '08:00',
  fin: '18:00',
});

/**
 * `D:1,2,3,4,5|08:00-18:00` (≤ 120 en backend).
 */
export function encodeHorarioStruct(s: HorarioStruct): string | null {
  const nums: number[] = [];
  for (let i = 0; i < 7; i++) {
    if (s.days[i]) {
      nums.push(i + 1);
    }
  }
  if (nums.length === 0) {
    return null;
  }
  const out = `D:${nums.join(',')}|${s.inicio}-${s.fin}`;
  return out.length <= 120 ? out : out.slice(0, 120);
}

export function decodeHorarioString(
  raw: string | null | undefined,
): { kind: 'struct'; value: HorarioStruct } | { kind: 'legacy'; text: string } | { kind: 'empty' } {
  if (!raw || !String(raw).trim()) {
    return { kind: 'empty' };
  }
  const t = String(raw).trim();
  const m = t.match(RE_ESTRUCT);
  if (!m) {
    return { kind: 'legacy', text: t };
  }
  const days: boolean[] = [false, false, false, false, false, false, false];
  for (const p of m[1].split(',')) {
    const n = Number(p);
    if (n >= 1 && n <= 7) {
      days[n - 1] = true;
    }
  }
  return {
    kind: 'struct',
    value: {
      days: days as HorarioStruct['days'],
      inicio: m[2],
      fin: m[3],
    },
  };
}

export function resumenHorarioEnTabla(hor: string | null | undefined): string {
  if (!hor || !String(hor).trim()) {
    return '—';
  }
  const s = String(hor).trim();
  const m = s.match(RE_ESTRUCT);
  if (!m) {
    return s;
  }
  const set = new Set(m[1].split(',').map((x) => Number(x)));
  const labels: string[] = [];
  for (let i = 0; i < 7; i++) {
    if (set.has(i + 1)) {
      labels.push(DIA_CORTO[i]);
    }
  }
  const días = labels.length > 0 ? labels.join(', ') : '—';
  return `${días} · ${m[2]}–${m[3]}`;
}
