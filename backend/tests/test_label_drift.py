"""Tests for observed ground-truth labels + the label-drift monitor.

Covers: placement dataset preferring real PlacementSelection records over the
simulated committee rule, meta provenance fields, and the drift report shape.
"""
import pytest
import uuid
from datetime import date

from app.db import SessionLocal
from app.ml.datasets import TASKS, build_all, build_placement_dataset, invalidate_dataset_cache
from app.models.entities import Company, PlacementDrive, PlacementSelection, Student
from app.services.label_drift import compute_label_drift
from synthetic.generator import SyntheticDataGenerator


def _make_drive(db) -> PlacementDrive:
    company = Company(name=f"DriftCo-{uuid.uuid4().hex[:10]}", sector="IT")
    db.add(company)
    db.flush()
    drive = PlacementDrive(title="Test Drive", company_id=company.id, drive_date=date(2026, 1, 10))
    db.add(drive)
    db.flush()
    return drive


@pytest.fixture(scope="module")
def seeded_db():
    """Small deterministic dataset (no selections yet -> all-simulated placement)."""
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
        # Same convention as main's own ML fixtures (e.g. tests/unit/ml/test_ml.py):
        # wipe every table the generator touched. `tests/api` runs first and owns
        # the admin login; no later unit test depends on it.
        for table in ("placement_selections", "placement_drives", "attendance", "results",
                      "enrollments", "timetable_entries", "courses", "lecturers", "students",
                      "rooms", "users"):
            db.execute(__import__("sqlalchemy").text(f"DELETE FROM {table}"))
        db.commit()
    finally:
        db.close()


def _any_student_uuid(db) -> str:
    return db.query(Student).first().id


def test_placement_simulated_when_no_selections(seeded_db) -> None:
    db = SessionLocal()
    try:
        dataset = build_placement_dataset(db)
        meta = dataset["meta"]
        assert meta["observed_labels"] == 0
        assert meta["simulated_labels"] == meta["rows"]
        assert meta["label_agreement"] is None
    finally:
        db.close()


def test_placement_observes_selection_records(seeded_db) -> None:
    db = SessionLocal()
    try:
        drive = _make_drive(db)
        student = db.query(Student).first()
        db.add(PlacementSelection(
            drive_id=drive.id, student_id=student.id, round_reached="HR",
            offered_ctc=8.0, offer_status="offered", decided_at=None,
        ))
        db.commit()
        invalidate_dataset_cache()

        dataset = build_placement_dataset(db)
        meta = dataset["meta"]
        assert meta["observed_labels"] == 1
        assert meta["simulated_labels"] == meta["rows"] - 1
        assert meta["label_agreement"] in (0, 1), "agreement must be computable"
        index = next(i for i, r in enumerate(dataset["ids"]) if r["student_id"] == student.student_id)
        assert dataset["y"][index] == 1, "offered student must be labelled placed (observed)"
    finally:
        db.close()


def test_drift_report_shape_and_coverage(seeded_db) -> None:
    db = SessionLocal()
    try:
        # drop any selections left by earlier tests so this test asserts the
        # all-simulated baseline deterministically
        from sqlalchemy import text

        db.execute(text("DELETE FROM placement_selections"))
        db.execute(text("DELETE FROM placement_drives"))
        db.commit()
        invalidate_dataset_cache()
        report = compute_label_drift(db)
        assert set(report["tasks"]) == set(TASKS)
        for task, info in report["tasks"].items():
            assert info["rows"] > 0
            assert "observed_labels" in info and "simulated_labels" in info
            assert info["drift_status"] in ("healthy", "drift", "no-observed-data", "unknown")
        # all-simulated state: placement reports no-observed-data, others too
        assert report["tasks"]["placement"]["drift_status"] == "no-observed-data"
        assert report["tasks"]["performance"]["observed_labels"] == 0
        assert report["generated_at"]
        assert report["agreement_threshold"] > 0
    finally:
        db.close()


def test_drift_status_healthy_after_observation(seeded_db) -> None:
    db = SessionLocal()
    try:
        drive = _make_drive(db)
        student = db.query(Student).first()
        db.add(PlacementSelection(
            drive_id=drive.id, student_id=student.id, round_reached="HR",
            offered_ctc=8.0, offer_status="offered", decided_at=None,
        ))
        db.commit()
        invalidate_dataset_cache()
        report = compute_label_drift(db)
        status = report["tasks"]["placement"]["drift_status"]
        assert status in ("healthy", "drift")
        assert report["tasks"]["placement"]["observed_labels"] == 1
    finally:
        db.close()
