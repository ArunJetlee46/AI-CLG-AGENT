"""Model primitives - numpy-only by design so training works offline.

The logistic regression is the guaranteed baseline. When requirements-ml.txt is
installed (scikit-learn / XGBoost / LightGBM), train.py swaps in the boosted
model behind the same Dataset/Metrics/Explain contracts (lazy imports).
"""
import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


class NumpyLogisticRegression:
    """L2-regularized logistic regression via gradient descent (pure numpy)."""

    def __init__(self, lr: float = 0.5, epochs: int = 400, l2: float = 1e-3, patience: int = 15) -> None:
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2
        self.patience = patience
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self.loss_history: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "NumpyLogisticRegression":
        n, d = X.shape
        w = np.zeros(d)
        b = 0.0
        best_loss = float("inf")
        best_w, best_b = w.copy(), b
        stale = 0
        for _ in range(self.epochs):
            p = sigmoid(X @ w + b)
            grad_w = X.T @ (p - y) / n + self.l2 * w
            grad_b = float(np.mean(p - y))
            w -= self.lr * grad_w
            b -= self.lr * grad_b
            eps = 1e-12
            loss = -np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)) + 0.5 * self.l2 * float(w @ w)
            self.loss_history.append(loss)
            if loss < best_loss - 1e-6:
                best_loss, best_w, best_b, stale = loss, w.copy(), b, 0
            else:
                stale += 1
                if stale >= self.patience:
                    break
        self.w, self.b = best_w, best_b
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        if self.w is None:
            raise RuntimeError("model not fitted")
        return X @ self.w + self.b

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return sigmoid(self.decision_function(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)


# ---------------------------------------------------------------------------
# Standardization
# ---------------------------------------------------------------------------


def fit_scaler(X: np.ndarray) -> dict[str, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std < 1e-9] = 1.0
    return {"mean": mean, "std": std}


def apply_scaler(X: np.ndarray, scaler: dict[str, np.ndarray]) -> np.ndarray:
    return (X - scaler["mean"]) / scaler["std"]


# ---------------------------------------------------------------------------
# Train / test split & metrics
# ---------------------------------------------------------------------------


def train_test_split(X: np.ndarray, y: np.ndarray, test_frac: float = 0.2, seed: int = 42):
    """Stratified split: preserves class balance in both folds (important for
    the imbalanced placement/dropout tasks)."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y))
    train_idx: list[int] = []
    test_idx: list[int] = []
    for label in (0, 1):
        group = idx[y == label]
        if len(group) < 2:
            train_idx.extend(group.tolist())
            continue
        group = rng.permutation(group)
        n_test = max(1, int(round(len(group) * test_frac)))
        n_test = min(n_test, len(group) - 1)
        test_idx.extend(group[:n_test].tolist())
        train_idx.extend(group[n_test:].tolist())
    train_idx = np.array(train_idx)
    test_idx = np.array(test_idx)
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx], train_idx, test_idx


def evaluate(y_true: np.ndarray, proba: np.ndarray) -> dict[str, float]:
    y_pred = (proba >= 0.5).astype(int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    accuracy = (tp + tn) / max(1, len(y_true))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    auc = _rank_auc(y_true, proba)
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "n": int(len(y_true)),
    }


def _rank_auc(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Mann-Whitney U based ROC-AUC - numpy-only, O(n log n)."""
    order = np.argsort(proba)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(proba) + 1)
    pos = y_true == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5  # uninformative: single-class fold
    u = float(ranks[pos].sum() - n_pos * (n_pos + 1) / 2)
    return float(u / (n_pos * n_neg))


# ---------------------------------------------------------------------------
# Explainability (linear-logit contributions; SHAP upgrade point)
# ---------------------------------------------------------------------------


def explain_logit(model: NumpyLogisticRegression, scaler: dict[str, np.ndarray], x_row: np.ndarray, features: list[str], top: int = 6) -> dict[str, Any]:
    """Per-feature contribution to the logit (weight * standardized value).

    This is the model-agnostic baseline explainer. When `shap` is installed
    (requirements-ml.txt), train/predict upgrades to TreeSHAP/KernelExplainer
    behind this same shape: {feature: contribution, _method: "..."}.
    """
    z = (x_row - scaler["mean"]) / scaler["std"]
    contributions = {f: float(model.w[i] * z[i]) for i, f in enumerate(features)}
    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top]
    return {"method": "linear-logit", "contributions": dict(ranked), "bias": float(model.b)}


def explain_shap(model: Any, scaler: dict[str, np.ndarray], x_row: np.ndarray, features: list[str], top: int = 6) -> dict[str, Any]:
    """Real SHAP explanation via the `shap` package.

    - Numpy logistic regression -> exact linear SHAP (LinearExplainer) on the
      scaled features, background = scaled training mean (zeros).
    - Boosted/tree models (XGBoost etc.) -> TreeExplainer.
    Falls back to `explain_logit` when shap is not installed or the explainer
    cannot handle the model. Same output shape: {method, contributions, bias}.
    """
    try:
        import shap  # noqa: WPS433 - lazy heavy import
    except ImportError:
        return explain_logit(model, scaler, x_row, features, top=top)

    try:
        z = (x_row - scaler["mean"]) / scaler["std"]
        method = "shap-linear"
        if hasattr(model, "w") and model.w is not None:
            coef = np.asarray(model.w, dtype=float).reshape(1, -1)
            intercept = np.asarray([float(model.b)], dtype=float)
            background = np.zeros((1, coef.shape[1]), dtype=float)
            explainer = shap.LinearExplainer((coef, intercept), shap.maskers.Independent(background))
            values = np.asarray(explainer.shap_values(z.reshape(1, -1)), dtype=float).reshape(-1)
            expected = explainer.expected_value
        else:
            method = "shap-tree"
            explainer = shap.TreeExplainer(model)
            raw = explainer.shap_values(z.reshape(1, -1))
            if isinstance(raw, list):
                raw = raw[1] if len(raw) > 1 else raw[0]
            values = np.asarray(raw, dtype=float).reshape(-1)
            expected = explainer.expected_value

        if isinstance(expected, (list, tuple, np.ndarray)):
            bias = float(np.asarray(expected).ravel()[0])
        else:
            bias = float(expected)
        contributions = {f: float(values[i]) for i, f in enumerate(features)}
        ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top]
        return {"method": method, "contributions": dict(ranked), "bias": bias}
    except Exception as exc:  # noqa: BLE001
        logger.warning("shap explainer failed (%s); using linear-logit baseline", exc)
        if hasattr(model, "w"):
            return explain_logit(model, scaler, x_row, features, top=top)
        return {"method": "shap-unavailable", "contributions": {}, "bias": 0.0}


# ---------------------------------------------------------------------------
# Persistence (numpy-only; no joblib dependency)
# ---------------------------------------------------------------------------


def save_model(model: NumpyLogisticRegression, scaler: dict[str, np.ndarray], features: list[str], meta: dict, model_dir: str, task: str) -> str:
    if model.w is None:
        raise RuntimeError("model not fitted")
    os.makedirs(model_dir, exist_ok=True)
    np_path = os.path.join(model_dir, f"{task}.npz")
    np.savez(np_path, w=model.w, b=np.array([model.b]), mean=scaler["mean"], std=scaler["std"], features=np.array(features))
    meta_path = os.path.join(model_dir, f"{task}_meta.json")
    meta["task"] = task
    meta["path"] = np_path
    meta["features"] = features
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, default=str)
    return np_path


def load_model(task: str, model_dir: str | None = None) -> dict[str, Any] | None:
    """Returns {model, scaler, features, meta} or None when not trained."""
    model_dir = model_dir or os.path.dirname(settings.prediction_model_path) or "models"
    np_path = os.path.join(model_dir, f"{task}.npz")
    meta_path = os.path.join(model_dir, f"{task}_meta.json")
    if not (os.path.exists(np_path) and os.path.exists(meta_path)):
        return None
    try:
        data = np.load(np_path, allow_pickle=False)
        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
        model = NumpyLogisticRegression()
        model.w = data["w"]
        model.b = float(np.asarray(data["b"]).item())
        return {
            "model": model,
            "scaler": {"mean": data["mean"], "std": data["std"]},
            "features": list(data["features"]),
            "meta": meta,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to load model %s: %s", task, exc)
        return None
