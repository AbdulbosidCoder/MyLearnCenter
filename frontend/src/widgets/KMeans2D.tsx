import { useMemo, useState } from "react";

import { Axes, Marker, Plot, Slider, gauss, makeScale, rng } from "./common";

type Pt = { x: number; y: number };

const BLOBS: Pt[] = [
  { x: 2.5, y: 2.5 },
  { x: 7.5, y: 3 },
  { x: 5, y: 7.5 },
  { x: 8, y: 8 },
];

function nearest(p: Pt, centers: Pt[]) {
  let best = 0;
  centers.forEach((c, i) => {
    if ((p.x - c.x) ** 2 + (p.y - c.y) ** 2 < (p.x - centers[best].x) ** 2 + (p.y - centers[best].y) ** 2) best = i;
  });
  return best;
}

export default function KMeans2D({ params }: { params: { k?: number } }) {
  const points = useMemo(() => {
    const rand = rng(3);
    return BLOBS.slice(0, 3).flatMap((b) => Array.from({ length: 18 }, () => ({ x: gauss(rand, b.x, 0.9), y: gauss(rand, b.y, 0.9) })));
  }, []);
  const [k, setK] = useState(Math.min(4, Math.max(2, params.k ?? 3)));
  const start = (count: number) => {
    const rand = rng(11 + count);
    return Array.from({ length: count }, () => ({ x: 1 + rand() * 8, y: 1 + rand() * 8 }));
  };
  const [centers, setCenters] = useState<Pt[]>(() => start(k));
  const [labels, setLabels] = useState<number[] | null>(null);
  const [step, setStep] = useState(0);
  const s = makeScale(0, 10, 0, 10);

  function reset(count = k) {
    setCenters(start(count));
    setLabels(null);
    setStep(0);
  }

  function next() {
    if (step % 2 === 0) {
      setLabels(points.map((p) => nearest(p, centers)));
    } else if (labels) {
      setCenters(
        centers.map((c, i) => {
          const mine = points.filter((_, j) => labels[j] === i);
          return mine.length
            ? { x: mine.reduce((a, p) => a + p.x, 0) / mine.length, y: mine.reduce((a, p) => a + p.y, 0) / mine.length }
            : c;
        }),
      );
    }
    setStep(step + 1);
  }

  return (
    <div className="viz">
      <Plot label={`Кластеризация k-means, k = ${k}, шаг ${step}`}>
        <Axes s={s} xTicks={[0, 5, 10]} yTicks={[0, 5, 10]} />
        {labels &&
          points.map((p, i) => (
            <line key={`l${i}`} x1={s.x(p.x)} y1={s.y(p.y)} x2={s.x(centers[labels[i]].x)} y2={s.y(centers[labels[i]].y)} className="viz-residual" />
          ))}
        {points.map((p, i) =>
          labels ? <Marker key={i} x={s.x(p.x)} y={s.y(p.y)} slot={labels[i]} size={3.5} /> : <circle key={i} cx={s.x(p.x)} cy={s.y(p.y)} r={3.5} className="viz-neutral" />,
        )}
        {centers.map((c, i) => (
          <g key={`c${i}`}>
            <Marker x={s.x(c.x)} y={s.y(c.y)} slot={i} size={8} />
            <text x={s.x(c.x) + 11} y={s.y(c.y) + 4} className="viz-label">
              {i + 1}
            </text>
          </g>
        ))}
      </Plot>
      <p className="viz-readout">
        {step === 0
          ? "Большие значки — центры кластеров. Нажмите «Шаг»."
          : step % 2 === 1
            ? "Шаг «назначить»: каждая точка выбрала ближайший центр."
            : "Шаг «сдвинуть»: каждый центр переехал в середину своих точек."}
      </p>
      <div className="viz-legend">
        {centers.map((_, i) => (
          <span key={i}>
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <Marker x={7} y={7} slot={i} size={4.5} />
            </svg>
            Кластер {i + 1}
          </span>
        ))}
      </div>
      <Slider
        label="Число кластеров k"
        value={k}
        min={2}
        max={4}
        step={1}
        onChange={(v) => {
          setK(v);
          reset(v);
        }}
      />
      <div className="viz-buttons">
        <button className="small" onClick={next}>
          Шаг
        </button>
        <button className="small chip" onClick={() => reset()}>
          Сначала
        </button>
      </div>
    </div>
  );
}
