function lerpColor(c1: string, c2: string, t: number): string {
  const parse = (h: string): [number, number, number] => [
    parseInt(h.slice(1, 3), 16),
    parseInt(h.slice(3, 5), 16),
    parseInt(h.slice(5, 7), 16),
  ];
  const [r1, g1, b1] = parse(c1);
  const [r2, g2, b2] = parse(c2);
  const blend = (a: number, b: number) => Math.round(a + (b - a) * t);
  const r = blend(r1, r2);
  const g = blend(g1, g2);
  const b = blend(b1, b2);
  return '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('');
}

// Red → Yellow → Green continuous scale; t in [0, 1].
export function rdYlGn(t: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  if (clamped < 0.5) return lerpColor('#d73027', '#ffffbf', clamped * 2);
  return lerpColor('#ffffbf', '#1a9850', (clamped - 0.5) * 2);
}

export function scaleValue(value: number, min: number, max: number): number {
  if (max === min) return 0.5;
  return (value - min) / (max - min);
}
