import logging

from app.db import SessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="synthetic.generate")
def generate_synthetic_data(students: int = 500, courses: int = 40, seed: int = 42) -> dict:
    from app.ml.datasets import invalidate_dataset_cache
    from synthetic.generator import SyntheticDataGenerator

    generator = SyntheticDataGenerator(students=students, courses=courses, seed=seed)
    bundle = generator.generate()
    db = SessionLocal()
    try:
        stats = generator.insert_to_db(db, bundle)
    finally:
        db.close()
    invalidate_dataset_cache()
    return {"students": students, "courses": courses, **stats}


@celery_app.task(name="ml.train")
def train_risk_model() -> dict:
    from app.ml.train import train_model

    return train_model()


@celery_app.task(name="ml.train_all")
def train_all_models() -> list[dict]:
    from app.ml.train import train_all

    return train_all()


@celery_app.task(name="ml.re_score")
def re_score_students() -> dict:
    db = SessionLocal()
    try:
        from app.core.audit import record_event
        from app.ml.predict import predict_risk

        results = predict_risk(db, limit=100)
        record_event(
            db,
            actor="celery",
            action="scheduled_rescore",
            entity_type="prediction",
            payload={"scored": len(results), "top_risk": results[0]["student_id"] if results else None},
        )
        return {"scored": len(results)}
    finally:
        db.close()
