import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.config import get_settings
from app.db import SessionLocal
from app.ml.datasets import TASKS, build_all
from app.ml.models import (
    NumpyLogisticRegression,
    apply_scaler,
    evaluate,
    fit_scaler,
    save_model,
    train_test_split,
)
from app.models.entities import ModelRecord

logger = logging.getLogger(__name__)
settings = get_settings()


def _fit_booster(dataset: dict, X_train: np.ndarray, X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray) -> tuple[Any, np.ndarray]:
    """XGBoost/LightGBM path - used only when requirements-ml.txt is installed."""
    import xgboost as xgb

    model = xgb.XGBClassifier(n_estimators=120, max_depth=4, learning_rate=0.08, eval_metric="logloss", verbosity=0)
    model.fit(X_train, y_train)
    model.version = f"xgb-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    proba = model.predict_proba(X_test)[:, 1]
    return model, proba


def train_task(task: str, model_dir: str | None = None, seed: int = 42, use_booster: bool = False) -> dict:
    """Train one task's model. numpy logistic regression is the guaranteed
    baseline; boosted trees (XGBoost) replace it when installed."""
    if task not in TASKS:
        return {"status": "failed", "error": f"unknown task '{task}'"}
    db = SessionLocal()
    try:
        datasets = build_all(db, seed=seed)
        dataset = datasets[task]
        if dataset["rows"] == 0:
            return {"status": "skipped", "task": task,
                    "reason": "no data; run the synthetic generator first (python -m synthetic.cli --students 500 --courses 40)"}

        X, y = dataset["X"], dataset["y"]
        X_train, X_test, y_train, y_test, _, _ = train_test_split(X, y, test_frac=0.2, seed=seed)
        scaler = fit_scaler(X_train)
        X_train_s, X_test_s = apply_scaler(X_train, scaler), apply_scaler(X_test, scaler)

        if use_booster:
            version = None
            try:
                model, proba_test = _fit_booster(dataset, X_train_s, X_test_s, y_train, y_test)
                algorithm = "xgboost"
                version = getattr(model, "version", f"xgb-{datetime.now(timezone.utc):%Y%m%d%H%M%S}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("boosted training unavailable (%s); falling back to logistic regression", exc)
                model, proba_test, algorithm = _fit_baseline(X_train_s, X_test_s, y_train), None, "logistic-regression"
                version = f"lr-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
        else:
            model, proba_test, algorithm = _fit_baseline(X_train_s, X_test_s, y_train)
            version = f"lr-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"

        metrics = evaluate(y_test, proba_test)
        model_dir = model_dir or "models"
        label_meta = {
            k: dataset["meta"].get(k)
            for k in ("observed_labels", "simulated_labels", "label_agreement")
        }
        path = save_model(model, scaler, dataset["features"],
                          {"algorithm": algorithm, "version": version, "metrics": metrics, "seed": seed,
                           "target_note": dataset["meta"].get("target_note"), "n_features": X.shape[1],
                           "label_drift": label_meta},
                          model_dir=model_dir, task=task)

        _record_model(db, task, version, path, metrics, algorithm)
        _mlflow_log(task, algorithm, metrics, path, dataset["rows"])
        return {"status": "trained", "task": task, "algorithm": algorithm, "rows": dataset["rows"],
                "version": version, "metrics": metrics, "path": path}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("training failed for %s", task)
        return {"status": "failed", "task": task, "error": str(exc)}
    finally:
        db.close()


def _fit_baseline(X_train_s, X_test_s, y_train):
    model = NumpyLogisticRegression().fit(X_train_s, y_train)
    proba_test = model.predict_proba(X_test_s)
    return model, proba_test, "logistic-regression"


def train_all(model_dir: str | None = None, seed: int = 42, use_booster: bool = False) -> list[dict]:
    return [train_task(task, model_dir=model_dir, seed=seed, use_booster=use_booster) for task in TASKS]


def train_model(model_dir: str | None = None) -> dict:
    """Back-compat wrapper (legacy celery task `ml.train`): trains dropout as the
    at-risk model. Returns the same shape as before."""
    result = train_task("dropout", model_dir=model_dir)
    if result.get("status") == "trained":
        return {"status": "trained", "rows": result["rows"], "version": result["version"],
                "path": result["path"], "metrics": result["metrics"]}
    return result


def _record_model(db, task: str, version: str, path: str, metrics: dict, algorithm: str) -> None:
    existing = db.query(ModelRecord).filter_by(name=f"{task}_model", version=version).first()
    if existing is None:
        db.add(ModelRecord(name=f"{task}_model", version=version, path=path,
                           metrics={"algorithm": algorithm, **metrics}))
        db.commit()


def _mlflow_log(task: str, algorithm: str, metrics: dict, path: str, rows: int) -> None:
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        with mlflow.start_run(run_name=f"{task}-{algorithm}"):
            mlflow.log_params({"task": task, "algorithm": algorithm, "rows": rows})
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"test_{key}", value)
            mlflow.log_artifact(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLflow logging skipped for %s: %s", task, exc)
