import { Component, lazy, Suspense, type ComponentType, type ReactNode } from "react";

import Derivative2D from "./Derivative2D";
import KMeans2D from "./KMeans2D";
import LinearRegression2D from "./LinearRegression2D";
import NormalDistribution2D from "./NormalDistribution2D";

// 3D widgets pull in three.js, so they load only when a lesson shows one.
const GradientDescent3D = lazy(() => import("./GradientDescent3D"));
const Scatter3D = lazy(() => import("./Scatter3D"));

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const REGISTRY: Record<string, ComponentType<{ params: any }>> = {
  "normal-distribution-2d": NormalDistribution2D,
  "linear-regression-2d": LinearRegression2D,
  "kmeans-2d": KMeans2D,
  "derivative-2d": Derivative2D,
  "gradient-descent-3d": GradientDescent3D,
  "scatter-3d": Scatter3D,
};

class Guard extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <p className="muted small">Не удалось показать визуализацию на этом устройстве.</p> : this.props.children;
  }
}

export function WidgetView({ content }: { content: string }) {
  let spec: { widget?: string; params?: object };
  try {
    spec = JSON.parse(content);
  } catch {
    return <p className="error">Визуализация повреждена.</p>;
  }
  const Widget = spec.widget ? REGISTRY[spec.widget] : undefined;
  if (!Widget) return <p className="error">Неизвестная визуализация: {spec.widget}</p>;
  return (
    <Guard>
      <Suspense fallback={<p className="muted center">Загрузка 3D…</p>}>
        <Widget params={spec.params ?? {}} />
      </Suspense>
    </Guard>
  );
}
