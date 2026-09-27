import { useState, type ReactNode, type PointerEvent } from "react";

/** Deterministic random numbers, so a widget shows the same data every time it opens. */
export function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Normal random value (Box–Muller). */
export function gauss(rand: () => number, mean = 0, sd = 1) {
  const u = Math.max(rand(), 1e-9);
  return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
}

/** Categorical colours (fixed order) and a marker shape per slot, so identity never rests on colour alone. */
export const SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];
export const SHAPES = ["circle", "square", "triangle", "diamond"] as const;

export function Marker({ x, y, slot, size = 4 }: { x: number; y: number; slot: number; size?: number }) {
  const fill = SERIES[slot % SERIES.length];
  const shape = SHAPES[slot % SHAPES.length];
  const common = { fill, stroke: "var(--viz-surface)", strokeWidth: 1.5 };
  if (shape === "circle") return <circle cx={x} cy={y} r={size} {...common} />;
  if (shape === "square") return <rect x={x - size} y={y - size} width={size * 2} height={size * 2} rx={1} {...common} />;
  if (shape === "triangle")
    return <path d={`M${x},${y - size * 1.2} L${x + size * 1.1},${y + size * 0.8} L${x - size * 1.1},${y + size * 0.8}Z`} {...common} />;
  return <path d={`M${x},${y - size * 1.3} L${x + size * 1.1},${y} L${x},${y + size * 1.3} L${x - size * 1.1},${y}Z`} {...common} />;
}

export const W = 320;
export const H = 220;
const PAD = { left: 30, right: 10, top: 10, bottom: 24 };

export interface Scale {
  x: (v: number) => number;
  y: (v: number) => number;
  invX: (px: number) => number;
}

export function makeScale(x0: number, x1: number, y0: number, y1: number): Scale {
  const iw = W - PAD.left - PAD.right;
  const ih = H - PAD.top - PAD.bottom;
  return {
    x: (v) => PAD.left + ((v - x0) / (x1 - x0)) * iw,
    y: (v) => PAD.top + ih - ((v - y0) / (y1 - y0)) * ih,
    invX: (px) => x0 + ((px - PAD.left) / iw) * (x1 - x0),
  };
}

/** Recessive axes with a few ticks. */
export function Axes({ s, xTicks, yTicks }: { s: Scale; xTicks: number[]; yTicks: number[] }) {
  return (
    <g className="viz-axis">
      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line x1={PAD.left} x2={W - PAD.right} y1={s.y(t)} y2={s.y(t)} className="viz-grid" />
          <text x={PAD.left - 4} y={s.y(t) + 3} textAnchor="end">
            {t}
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <text key={`x${t}`} x={s.x(t)} y={H - 8} textAnchor="middle">
          {t}
        </text>
      ))}
    </g>
  );
}

/** SVG chart area that reports the pointer position in chart units (for hover and dragging). */
export function Plot({
  children,
  label,
  onPointer,
  onLeave,
}: {
  children: ReactNode;
  label: string;
  onPointer?: (px: number, py: number, pressed: boolean) => void;
  onLeave?: () => void;
}) {
  const [pressed, setPressed] = useState(false);
  function handle(e: PointerEvent<SVGSVGElement>, down = pressed) {
    if (!onPointer) return;
    const rect = e.currentTarget.getBoundingClientRect();
    onPointer(((e.clientX - rect.left) / rect.width) * W, ((e.clientY - rect.top) / rect.height) * H, down);
  }
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="viz-svg"
      role="img"
      aria-label={label}
      onPointerDown={(e) => {
        setPressed(true);
        e.currentTarget.setPointerCapture(e.pointerId);
        handle(e, true);
      }}
      onPointerUp={() => setPressed(false)}
      onPointerMove={(e) => handle(e)}
      onPointerLeave={() => {
        setPressed(false);
        onLeave?.();
      }}
    >
      {children}
    </svg>
  );
}

export function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="viz-slider">
      <span>
        {label}: <strong>{value.toFixed(step < 1 ? 2 : 0)}</strong>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

export function fmt(v: number, digits = 2) {
  return Number.isInteger(v) ? String(v) : v.toFixed(digits);
}
