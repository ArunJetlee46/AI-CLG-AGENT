from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import require_role
from app.db import SessionLocal
from app.models.entities import User
from app.schemas.admin import GenerateRequest

router = APIRouter(prefix="/synthetic", tags=["synthetic"])


def _generate_in_background(students: int, courses: int, seed: int) -> None:
    from app.core.audit import record_event
    from app.ml.datasets import invalidate_dataset_cache
    from synthetic.generator import SyntheticDataGenerator

    generator = SyntheticDataGenerator(students=students, courses=courses, seed=seed)
    bundle = generator.generate()
    db = SessionLocal()
    try:
        stats = generator.insert_to_db(db, bundle)
        record_event(db, actor="synthetic-api", action="data_generated", entity_type="dataset", payload=stats)
    finally:
        db.close()
    invalidate_dataset_cache()


@router.post("/generate")
def generate(
    body: GenerateRequest,
    background: BackgroundTasks,
    _: User = Depends(require_role("admin")),
) -> dict:
    background.add_task(_generate_in_background, body.students, body.courses, body.seed)
    return {"status": "queued", "students": body.students, "courses": body.courses, "seed": body.seed}
