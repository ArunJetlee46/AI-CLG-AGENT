import numpy as np
import pytest

from app.db import SessionLocal
from app.ml.datasets import TASKS, build_all
from app.ml.models import (
    NumpyLogisticRegression,
    apply_scaler,
    evaluate,
    explain_logit,
    fit_scaler,
    load_model,
    save_model,
    train_test_split,
)
from app.ml.predict import predict_risk, predict_task
from app.ml.train import train_all, train_model, train_task
from synthetic.generator import SyntheticDataGenerator


@pytest.fixture(scope="module")
def seeded_db():
    """Small deterministic dataset with embedded failure patterns."""
    generator = SyntheticDataGenerator(students=30, courses=6, seed=7)
    bundle = generator.generate()
    db = SessionLocal()
    try:
        generator.insert_to_db(db, bundle)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        for table in ("attendance", "results", "enrollments", "timetable_entries",
                      "courses", "lecturers", "students", "rooms", "users"):
            db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
        db.commit()
    finally:
        db.close()


def test_all_datasets_build(seeded_db) -> None:
    db = SessionLocal()
    try:
        datasets = build_all(db)
        assert set(datasets) == set(TASKS)
        for task in TASKS:
            dataset = datasets[task]
            assert dataset["rows"] > 0, task
            assert dataset["X"].shape[0] == dataset["y"].shape[0]
            assert set(np.unique(dataset["y"])) <= {0, 1}
            assert dataset["X"].shape[1] == len(dataset["features"])
            assert dataset["meta"]["pos_rate"] is not None
    finally:
        db.close()


def test_train_test_split_and_metrics() -> None:
    X = np.arange(40).reshape(20, 2).astype(float)
    y = np.array([0, 1] * 10)
    X_tr, X_te, y_tr, y_te, tr_idx, te_idx = train_test_split(X, y, test_frac=0.3, seed=1)
    # stratified: 30% of each class -> 3 per class in test -> 6 test / 14 train
    assert len(y_tr) == 14 and len(y_te) == 6
    assert y_te.sum() == 3, "stratified split must keep class balance"
    assert set(tr_idx).isdisjoint(set(te_idx))

    metrics = evaluate(y_te, np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.4]))
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert 0.0 <= metrics[key] <= 1.0


def test_auc_uninformative_on_single_class() -> None:
    metrics = evaluate(np.array([1, 1, 1]), np.array([0.2, 0.4, 0.6]))
    assert metrics["roc_auc"] == 0.5


def test_logistic_regression_learns_separable_rule() -> None:
    rng = np.random.default_rng(3)
    X = rng.normal(size=(400, 3))
    y = (X[:, 0] + 2 * X[:, 1] - X[:, 2] > 0).astype(int)
    X_tr, X_te, y_tr, y_te, _, _ = train_test_split(X, y, seed=3)
    scaler = fit_scaler(X_tr)
    model = NumpyLogisticRegression().fit(apply_scaler(X_tr, scaler), y_tr)
    proba = model.predict_proba(apply_scaler(X_te, scaler))
    metrics = evaluate(y_te, proba)
    assert metrics["accuracy"] > 0.85


def test_save_load_roundtrip_and_explain() -> None:
    rng = np.random.default_rng(5)
    X = rng.normal(size=(100, 2))
    y = (X[:, 0] > 0).astype(int)
    scaler = fit_scaler(X)
    model = NumpyLogisticRegression().fit(apply_scaler(X, scaler), y)
    path = save_model(model, scaler, ["gpa", "attendance"], {"version": "test-v1"}, model_dir="models_test", task="dropout")
    pack = load_model("dropout", model_dir="models_test")
    assert pack is not None
    proba = pack["model"].predict_proba(apply_scaler(X[:5], pack["scaler"]))
    assert ((proba >= 0) & (proba <= 1)).all()
    explanation = explain_logit(pack["model"], pack["scaler"], X[0], ["gpa", "attendance"])
    assert explanation["method"] == "linear-logit"
    assert set(explanation["contributions"]) == {"gpa", "attendance"}
    import os

    os.remove(path)
    os.remove("models_test/dropout_meta.json")


def test_train_all_and_predict(seeded_db, tmp_path) -> None:
    results = train_all(model_dir=str(tmp_path))
    assert len(results) == 4
    for result in results:
        assert result["status"] == "trained"
        assert result["metrics"]["roc_auc"] is not None

    db = SessionLocal()
    try:
        for task in TASKS:
            rows = predict_task(db, task, limit=5, model_dir=str(tmp_path))
            assert rows, task
            for row in rows:
                assert row["student_id"]
                assert row["explanation"]
                assert row["model_version"].startswith("lr-")
                assert row["risk_level"] in ("low", "medium", "high")
        risk = predict_risk(db, limit=5)
        assert risk and set(risk[0]) == {"student_id", "course_code", "probability",
                                         "risk_level", "explanation", "model_version", "shap"}
    finally:
        db.close()


def test_train_model_backcompat(seeded_db, tmp_path) -> None:
    result = train_model(model_dir=str(tmp_path))
    assert result["status"] in ("trained", "skipped")