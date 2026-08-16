from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db import get_db
from app.ml.predict import predict_all, predict_risk
from app.models.entities import ModelRecord, Prediction
from app.schemas.common import PredictionOut
from app.services.label_drift import compute_label_drift

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=list[PredictionOut])
def list_predictions(limit: int = 50, db: Session = Depends(get_db), _=Depends(require_role("admin", "lecturer", "placement"))) -> list[Prediction]:
    return list(db.execute(select(Prediction).order_by(Prediction.created_at.desc()).limit(limit)).scalars())


@router.get("/models")
def list_models(db: Session = Depends(get_db), _=Depends(require_role("admin", "lecturer", "placement"))) -> list[dict]:
    """Model registry: trained task models + evaluation metrics (Phase 9)."""
    records = db.execute(select(ModelRecord).order_by(ModelRecord.trained_at.desc())).scalars().all()
    return [
        {
            "name": m.name,
            "version": m.version,
            "path": m.path,
            "metrics": m.metrics,
            "trained_at": m.trained_at.isoformat(),
        }
        for m in records
    ]


@router.get("/live")
def live_predictions(db: Session = Depends(get_db), _=Depends(require_role("admin", "lecturer", "placement"))) -> list[dict]:
    """On-the-fly scoring with explanations (no scheduled model required)."""
    return predict_risk(db, limit=25)


@router.get("/all")
def all_predictions(limit: int = 25, db: Session = Depends(get_db), _=Depends(require_role("admin", "lecturer", "placement"))) -> list[dict]:
    """All four Phase-9 tasks scored (performance, placement, attendance, dropout)."""
    return predict_all(db, limit=limit)


@router.get("/label-drift")
def label_drift(db: Session = Depends(get_db), _=Depends(require_role("admin", "lecturer", "placement"))) -> dict:
    """Label provenance + drift report: observed vs simulated ground truth per task."""
    return compute_label_drift(db)

