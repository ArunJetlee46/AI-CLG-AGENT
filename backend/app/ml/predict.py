import logging

import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.ml.datasets import TASKS, build_all
from app.ml.models import apply_scaler, explain_shap, load_model

logger = logging.getLogger(__name__)
settings = get_settings()

TASK_LABELS = {
    "performance": ("pass_probability", "pass"),
    "placement": ("placement_probability", "placed"),
    "attendance": ("absence_risk", "absentee"),
    "dropout": ("dropout_probability", "at-risk"),
}


def _heuristic_proba(task: str, dataset: dict, i: int) -> float:
    """Deterministic fallback when no model is trained yet (mirrors old risk heuristic)."""
    features = dataset["features"]
    row = {name: float(dataset["X"][i][j]) for j, name in enumerate(features)}
    if task == "dropout":
        return max(0.0, min(1.0, 0.45 * (1 - row.get("attendance_rate", 0.5))
                            + 0.35 * (1 - min(1.0, row.get("gpa", 0) / 4.0))
                            + 0.2 * (1 - min(1.0, row.get("avg_marks", 0) / 100))))
    if task == "attendance":
        return max(0.0, min(1.0, 1 - row.get("attendance_mean", 0.5)))
    if task == "performance":
        return max(0.0, min(1.0, 0.5 * (row.get("attendance_rate", 0.5))
                            + 0.5 * min(1.0, row.get("gpa", 0) / 4.0)))
    return max(0.0, min(1.0, 0.6 * (row.get("gpa", 0) / 4.0) + 0.4 * row.get("attendance_rate", 0.5)))


def predict_task(db: Session, task: str, limit: int = 25, model_dir: str | None = None) -> list[dict]:
    """Score a task's dataset; explain the top rows. Uses the trained model when
    available, else a labelled deterministic heuristic."""
    if task not in TASKS:
        return []
    dataset = build_all(db)[task]
    if dataset["rows"] == 0:
        return []

    model_pack = load_model(task, model_dir=model_dir)
    proba_key, action_label = TASK_LABELS[task]
    if model_pack is not None:
        X = dataset["X"]
        proba = model_pack["model"].predict_proba(apply_scaler(X, model_pack["scaler"]))
        model_version = model_pack["meta"].get("version", "unknown")
        method = "model"
    else:
        proba = np.array([_heuristic_proba(task, dataset, i) for i in range(dataset["rows"])])
        model_version = "heuristic-v1"
        method = "heuristic"

    results: list[dict] = []
    for i in np.argsort(proba)[::-1][:limit]:
        row = dataset["X"][int(i)]
        explanation = _explain(model_pack, row, dataset["features"], proba[int(i)], method)
        results.append(
            {
                "task": task,
                "student_id": dataset["ids"][int(i)]["student_id"],
                "course_code": dataset["ids"][int(i)].get("course_code"),
                proba_key: round(float(proba[int(i)]), 4),
                "risk_level": "high" if proba[int(i)] >= 0.7 else ("medium" if proba[int(i)] >= 0.4 else "low"),
                "action": action_label,
                "explanation": explanation["text"],
                "explainer": explanation["method"],
                "contributions": explanation["contributions"],
                "model_version": model_version,
            }
        )
    return results


def predict_all(db: Session, limit: int = 25) -> list[dict]:
    out: list[dict] = []
    for task in TASKS:
        out.extend(predict_task(db, task, limit=limit))
    return sorted(out, key=lambda r: r.get("probability", r.get("pass_probability", r.get("placement_probability",
                                 r.get("absence_risk", r.get("dropout_probability", 0))))), reverse=True)


def _explain(model_pack: dict | None, row: np.ndarray, features: list[str], proba: float, method: str) -> dict:
    if model_pack is not None:
        explanation = explain_shap(model_pack["model"], model_pack["scaler"], row, features, top=6)
        contributions = explanation["contributions"]
        explainer = explanation["method"]
        drivers = [f"{name} ({sign:+})" for name, sign in sorted(contributions.items(),
                                                                  key=lambda kv: abs(kv[1]), reverse=True)[:4]]
        text = f"drivers: {'; '.join(drivers)}" if drivers else "no strong drivers"
        return {"method": explainer, "contributions": contributions, "text": text}
    # heuristic fallback: show raw feature values as context
    named = {f: round(float(row[i]), 3) for i, f in enumerate(features[:6])}
    return {"method": f"heuristic-{method}", "contributions": named,
            "text": f"heuristic score {proba:.0%}; features: {named}"}


# ---------------------------------------------------------------------------
# Back-compat: predict_risk (used by /predictions/live and the success agent)
# ---------------------------------------------------------------------------


def predict_risk(db: Session, limit: int = 10) -> list[dict]:
    """At-risk prediction (dropout task). Returns the legacy shape:
    {student_id, course_code, probability, risk_level, explanation,
     model_version, shap}."""
    results = predict_task(db, "dropout", limit=limit)
    return [
        {
            "student_id": r["student_id"],
            "course_code": r["course_code"],
            "probability": r["dropout_probability"],
            "risk_level": r["risk_level"],
            "explanation": r["explanation"],
            "model_version": r["model_version"],
            "shap": r["contributions"],
        }
        for r in results
    ]
