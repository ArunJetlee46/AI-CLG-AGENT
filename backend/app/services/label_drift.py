"""Label-drift monitoring for the ML pipeline.

Reports, per prediction task, how much the simulated committee-rule labels
have drifted from observed ground truth. Today only `placement` can carry
observed labels (PlacementSelection records); the remaining tasks are reported
as simulated-only so the dashboard shows exactly where ground truth is missing.

Agreement is measured against the *deterministic* committee-rule prediction
(the logistic score sign) rather than the seeded-noisy label, so a drop in
agreement reflects a genuine rule-vs-reality divergence, not RNG noise.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ml.datasets import TASKS, build_all

logger = logging.getLogger(__name__)

DRIFT_AGREEMENT_THRESHOLD = 0.75


def _drift_status(task: str, meta: dict) -> str:
    observed = int(meta.get("observed_labels", 0))
    agreement = meta.get("label_agreement")
    if observed == 0:
        return "no-observed-data"
    if agreement is None:
        return "unknown"
    if agreement < DRIFT_AGREEMENT_THRESHOLD:
        return "drift"
    return "healthy"


def compute_label_drift(db: Session) -> dict:
    """Snapshot of label provenance + drift across all prediction tasks.

    `use_cache=False` deliberately: drift monitoring must reflect the latest
    records, not a cached snapshot.
    """
    datasets = build_all(db, use_cache=False)
    tasks: dict[str, dict] = {}
    for task in TASKS:
        meta = datasets[task]["meta"]
        tasks[task] = {
            "rows": int(meta.get("rows", 0)),
            "pos_rate": meta.get("pos_rate"),
            "observed_labels": int(meta.get("observed_labels", 0)),
            "simulated_labels": int(meta.get("simulated_labels", meta.get("rows", 0))),
            "label_agreement": meta.get("label_agreement"),
            "target_note": meta.get("target_note", ""),
            "drift_status": _drift_status(task, meta),
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agreement_threshold": DRIFT_AGREEMENT_THRESHOLD,
        "tasks": tasks,
    }
