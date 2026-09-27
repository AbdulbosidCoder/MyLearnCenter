"""Interactive visualizations a lesson can show. The Mini App draws them (frontend/src/widgets).

A "viz" block stores {"widget": <name>, "params": {...}} as JSON in its content.
The descriptions are also shown to the AI agent so it can pick a fitting one for a lesson.
"""

import json

WIDGETS: dict[str, dict] = {
    "normal-distribution-2d": {
        "title": "Нормальное распределение",
        "about": "Bell curve with sliders for mean and standard deviation; shades the area within one sigma. "
        "For statistics, probability, variance, z-scores.",
        "params": {"mean": 0, "sd": 1},
    },
    "linear-regression-2d": {
        "title": "Линейная регрессия",
        "about": "Scatter of noisy points; the student moves slope and intercept and sees the squared error, "
        "then can show the best-fit line. For regression, least squares, loss functions.",
        "params": {"points": 20, "noise": 1.5},
    },
    "kmeans-2d": {
        "title": "Кластеризация k-means",
        "about": "Points and k centroids; each step assigns points and moves centroids. "
        "For clustering, unsupervised learning, iterative algorithms.",
        "params": {"k": 3},
    },
    "derivative-2d": {
        "title": "Скорость изменения",
        "about": "A curve with a draggable point and its tangent line; shows the slope as the speed of change. "
        "For derivatives, speed, gradients, rate of change.",
        "params": {"fn": "x^2"},
    },
    "gradient-descent-3d": {
        "title": "Градиентный спуск в 3D",
        "about": "A ball rolls down a 3D loss surface step by step; the learning rate is a slider. "
        "For optimization, gradient descent, learning rate, training neural networks.",
        "params": {"lr": 0.1},
    },
    "scatter-3d": {
        "title": "Данные в трёх измерениях",
        "about": "A rotatable 3D cloud of points in clusters that can be flattened to 2D. "
        "For features and dimensions, dimensionality reduction, PCA, vectors.",
        "params": {"clusters": 3},
    },
}


def parse_viz(content: str) -> dict:
    """Checks a viz block's JSON; raises ValueError with a readable message."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("viz content must be JSON") from exc
    if not isinstance(data, dict) or data.get("widget") not in WIDGETS:
        raise ValueError(f"widget must be one of: {', '.join(WIDGETS)}")
    if not isinstance(data.get("params", {}), dict):
        raise ValueError("params must be an object")
    return data


def viz_content(widget: str) -> str:
    return json.dumps({"widget": widget, "params": WIDGETS[widget]["params"]})
