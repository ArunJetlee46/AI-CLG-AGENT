"""Faculty Copilot services.

Deterministic, explainable faculty-facing analytics built on the ML prediction
layer, the attendance records and the approval-gated intervention flow:

  overview        -> class performance intelligence (avg/high/low, risk bands,
                     trends) across the lecturer's authorized courses
  at-risk         -> at-risk student monitor with human-readable reasons
  course health   -> 0-100 course health score with components
  attendance      -> students below the 75% threshold, course-scoped
  interventions   -> propose approval-gated intervention plans

The demo `lecturer` account has no Lecturer row; `resolve_lecturer` falls back
to `settings.demo_lecturer_id` (LEC0000).
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.audit import record_event
from app.models.entities import (
    ApprovalRequest,
    AttendanceRecord,
    AuditLog,
    Course,
    Enrollment,
    InterventionPlan,
    Lecturer,
    Result,
    Student,
    TimetableEntry,
    User,
)

settings = get_settings()

ATTENDANCE_MIN = 0.75  # KB rule: below 75% -> ineligible to sit the exam
PASS_PROB_BANDS = (0.4, 0.7)


def resolve_lecturer(db: Session, user: User) -> Lecturer | None:
    """Map an authenticated user to the Lecturer row they own."""
    if user.lecturer is not None:
        return user.lecturer
    linked = db.execute(select(Lecturer).where(Lecturer.staff_id == user.username)).scalar_one_or_none()
    if linked is not None:
        return linked
    demo = db.execute(select(Lecturer).where(Lecturer.staff_id == settings.demo_lecturer_id)).scalar_one_or_none()
    if demo is not None:
        return demo
    return db.execute(select(Lecturer).order_by(Lecturer.staff_id)).scalars().first()


def _lecturer_course_ids(db: Session, lecturer: Lecturer) -> set[str]:
    return {
        entry.course_id
        for entry in db.execute(select(TimetableEntry).where(TimetableEntry.lecturer_id == lecturer.id)).scalars()
    }


def _attendance_rate(db: Session, enrollment_id: str) -> float:
    present = db.execute(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.enrollment_id == enrollment_id, AttendanceRecord.status == "present"
        )
    ).scalar_one()
    total = db.execute(
        select(func.count(AttendanceRecord.id)).where(AttendanceRecord.enrollment_id == enrollment_id)
    ).scalar_one()
    return present / total if total else 0.5


def _attendance_trend(db: Session, enrollment_id: str) -> float:
    """Slope of the attendance rate across weekly buckets (negative = declining)."""
    records = db.execute(
        select(AttendanceRecord).where(AttendanceRecord.enrollment_id == enrollment_id).order_by(AttendanceRecord.day)
    ).scalars().all()
    if len(records) < 8:
        return 0.0
    start = records[0].day
    weekly: dict[int, list[int]] = {}
    for record in records:
        week = (record.day - start).days // 7
        weekly.setdefault(week, []).append(1 if record.status == "present" else 0)
    weeks = sorted(weekly)
    if len(weeks) < 2:
        return 0.0
    rates = [sum(weekly[w]) / len(weekly[w]) for w in weeks]
    n = len(rates)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(rates) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    return round(sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, rates)) / denom, 4) if denom else 0.0


def _dropout_proba(gpa: float, attendance: float, avg_marks: float) -> float:
    """Mirror of ml.predict._heuristic_proba("dropout")."""
    value = 0.45 * (1 - attendance) + 0.35 * (1 - min(1.0, gpa / 4.0)) + 0.2 * (1 - min(1.0, avg_marks / 100.0))
    return max(0.0, min(1.0, value))


def _risk_band(proba: float) -> str:
    return "high" if proba >= PASS_PROB_BANDS[1] else ("medium" if proba >= PASS_PROB_BANDS[0] else "low")


def _course_rows(db: Session, course_ids: set[str]) -> list[dict]:
    """One row per approved enrollment in the given courses, with aggregates."""
    enrollments = db.execute(
        select(Enrollment, Student, Course)
        .join(Student, Enrollment.student_id == Student.id)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.status == "approved", Enrollment.course_id.in_(course_ids))
    ).all()
    rows: list[dict] = []
    for enrollment, student, course in enrollments:
        rate = _attendance_rate(db, enrollment.id)
        result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        marks = result.marks if result else None
        grade = result.grade if result else ""
        rows.append(
            {
                "enrollment_id": enrollment.id,
                "student_id": student.student_id,
                "student_uuid": student.id,
                "course_code": course.code,
                "course_title": course.title,
                "course_id": course.id,
                "gpa": float(student.gpa or 0.0),
                "attendance_rate": rate,
                "attendance_trend": _attendance_trend(db, enrollment.id),
                "marks": round(marks, 1) if marks is not None else None,
                "grade": grade,
            }
        )
    return rows


def get_profile(db: Session, lecturer: Lecturer) -> dict:
    course_ids = _lecturer_course_ids(db, lecturer)
    courses = db.execute(
        select(Course).where(Course.id.in_(course_ids)).order_by(Course.code)
    ).scalars().all()
    rows = _course_rows(db, course_ids)
    students = {r["student_uuid"] for r in rows}
    hours = 0.0
    for entry in db.execute(select(TimetableEntry).where(TimetableEntry.lecturer_id == lecturer.id)).scalars():
        duration = (entry.end_time.hour * 60 + entry.end_time.minute
                    - (entry.start_time.hour * 60 + entry.start_time.minute)) / 60
        hours += max(0.0, duration)
    return {
        "staff_id": lecturer.staff_id,
        "department": lecturer.department,
        "max_hours": lecturer.max_hours,
        "courses": [{"course_code": c.code, "title": c.title, "credits": c.credits} for c in courses],
        "course_count": len(courses),
        "student_count": len(students),
        "teaching_hours": round(hours, 1),
    }


def get_overview(db: Session, lecturer: Lecturer) -> dict:
    course_ids = _lecturer_course_ids(db, lecturer)
    rows = _course_rows(db, course_ids)
    if not rows:
        return {"student_count": 0, "rows": 0, "courses": [], "summary": {}, "trends": []}

    by_course: dict[str, list[dict]] = {}
    for row in rows:
        by_course.setdefault(row["course_code"], []).append(row)

    courses_summary: list[dict] = []
    declining: list[dict] = []
    for code in sorted(by_course):
        group = by_course[code]
        marks = [r["marks"] for r in group if r["marks"] is not None]
        graded = [r for r in group if r["grade"]]
        pass_rate = sum(1 for r in graded if r["grade"] != "F") / len(graded) if graded else 0.0
        probs = [_dropout_proba(r["gpa"], r["attendance_rate"], r["marks"] or 0.0) for r in group]
        at_risk = sum(1 for p in probs if p >= PASS_PROB_BANDS[1])
        avg_trend = sum(r["attendance_trend"] for r in group) / len(group)
        strong = sum(1 for p in probs if p < PASS_PROB_BANDS[0])
        courses_summary.append(
            {
                "course_code": code,
                "title": group[0]["course_title"],
                "enrolled": len(group),
                "avg_marks": round(sum(marks) / len(marks), 1) if marks else None,
                "highest": round(max(marks), 1) if marks else None,
                "lowest": round(min(marks), 1) if marks else None,
                "pass_rate": round(pass_rate, 4),
                "at_risk_count": at_risk,
                "strong_count": strong,
                "attendance_trend": round(avg_trend, 4),
            }
        )
        if avg_trend < -0.01:
            declining.append(
                {
                    "course_code": code,
                    "title": group[0]["course_title"],
                    "detail": f"Attendance trend in {code} is declining ({avg_trend:+.0%}/week).",
                }
            )

    all_marks = [r["marks"] for r in rows if r["marks"] is not None]
    graded = [r for r in rows if r["grade"]]
    pass_rate = sum(1 for r in graded if r["grade"] != "F") / len(graded) if graded else 0.0
    probs = [_dropout_proba(r["gpa"], r["attendance_rate"], r["marks"] or 0.0) for r in rows]
    summary = {
        "students": len({r["student_uuid"] for r in rows}),
        "rows": len(rows),
        "average": round(sum(all_marks) / len(all_marks), 1) if all_marks else None,
        "highest": round(max(all_marks), 1) if all_marks else None,
        "lowest": round(min(all_marks), 1) if all_marks else None,
        "pass_rate": round(pass_rate, 4),
        "strong": sum(1 for p in probs if p < PASS_PROB_BANDS[0]),
        "average_band": sum(1 for p in probs if PASS_PROB_BANDS[0] <= p < PASS_PROB_BANDS[1]),
        "at_risk": sum(1 for p in probs if p >= PASS_PROB_BANDS[1]),
    }

    return {
        "student_count": summary["students"],
        "rows": summary["rows"],
        "summary": summary,
        "courses": courses_summary,
        "trends": sorted(declining, key=lambda d: d["course_code"]),
    }


def get_at_risk(db: Session, lecturer: Lecturer, limit: int = 50) -> list[dict]:
    course_ids = _lecturer_course_ids(db, lecturer)
    rows = _course_rows(db, course_ids)
    scored: list[dict] = []
    for row in rows:
        proba = _dropout_proba(row["gpa"], row["attendance_rate"], row["marks"] or 0.0)
        reasons: list[str] = []
        if row["attendance_rate"] < ATTENDANCE_MIN:
            reasons.append(f"attendance {row['attendance_rate']:.0%} below 75%")
        if row["gpa"] < 2.5:
            reasons.append(f"GPA {row['gpa']} below 2.5")
        if row["marks"] is not None and row["marks"] < 50:
            reasons.append(f"marks {row['marks']} below 50")
        if row["grade"] == "F":
            reasons.append("failing grade (F)")
        if row["attendance_trend"] < -0.02:
            reasons.append("declining attendance trend")
        if not reasons:
            reasons.append("stable performance")
        scored.append(
            {
                "student_id": row["student_id"],
                "course_code": row["course_code"],
                "course_title": row["course_title"],
                "gpa": row["gpa"],
                "attendance_rate": row["attendance_rate"],
                "marks": row["marks"],
                "grade": row["grade"],
                "probability": round(proba, 4),
                "risk_level": _risk_band(proba),
                "reasons": reasons,
            }
        )
    scored.sort(key=lambda s: s["probability"], reverse=True)
    return scored[:limit]


def get_course_health(db: Session, lecturer: Lecturer, course_code: str) -> dict:
    course = db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()
    course_ids = _lecturer_course_ids(db, lecturer)
    if course is None:
        return {"course_code": course_code, "exists": False}
    if course.id not in course_ids:
        return {"course_code": course_code, "exists": True, "authorized": False}

    rows = [r for r in _course_rows(db, {course.id})]
    if not rows:
        return {"course_code": course_code, "exists": True, "authorized": True, "enrolled": 0, "health_score": None}

    graded = [r for r in rows if r["grade"]]
    pass_rate = sum(1 for r in graded if r["grade"] != "F") / len(graded) if graded else 0.0
    attendance_mean = sum(r["attendance_rate"] for r in rows) / len(rows)
    failure_rate = 1.0 - pass_rate
    marks = [r["marks"] for r in rows if r["marks"] is not None]
    performance = sum(marks) / len(marks) / 100.0 if marks else 0.0

    health = max(0.0, min(100.0, 100.0 * (0.35 * attendance_mean + 0.40 * performance + 0.25 * (1 - failure_rate))))
    health = int(round(health))
    band = "healthy" if health >= 75 else ("warning" if health >= 55 else "at-risk")

    return {
        "course_code": course_code,
        "course_title": course.title,
        "exists": True,
        "authorized": True,
        "enrolled": len(rows),
        "health_score": health,
        "band": band,
        "components": {
            "attendance": round(attendance_mean, 4),
            "performance": round(performance, 4),
            "pass_rate": round(pass_rate, 4),
            "failure_rate": round(failure_rate, 4),
        },
        "drivers": [
            f"attendance average {attendance_mean:.0%}",
            f"pass rate {pass_rate:.0%}",
            f"failure rate {failure_rate:.0%}",
        ],
    }


def get_course_attendance(db: Session, lecturer: Lecturer, course_code: str, threshold: float = ATTENDANCE_MIN) -> dict:
    course = db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()
    if course is None:
        return {"course_code": course_code, "exists": False}
    course_ids = _lecturer_course_ids(db, lecturer)
    if course.id not in course_ids:
        return {"course_code": course_code, "exists": True, "authorized": False}

    rows = [r for r in _course_rows(db, {course.id})]
    below = sorted(
        [r for r in rows if r["attendance_rate"] < threshold],
        key=lambda r: r["attendance_rate"],
    )
    return {
        "course_code": course_code,
        "course_title": course.title,
        "exists": True,
        "authorized": True,
        "threshold": threshold,
        "enrolled": len(rows),
        "below_count": len(below),
        "students": [
            {
                "student_id": r["student_id"],
                "attendance_rate": r["attendance_rate"],
                "gpa": r["gpa"],
                "grade": r["grade"],
            }
            for r in below
        ],
    }


def propose_intervention(
    db: Session, lecturer: Lecturer, *, student_id: str, course_code: str, plan_text: str,
    actor_user_id: str | None = None,
) -> dict:
    """Propose an intervention for a student in one of the lecturer's courses.

    Propose-only: creates a pending ApprovalRequest owned by the acting user
    (so the HITL decide gate can verify proposer == decider). The existing
    `POST /approvals/{id}` gate approves it, then the Execute Agent persists
    the InterventionPlan through execution.apply_intervention.
    """
    course = db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()
    if course is None:
        raise ValueError(f"course {course_code} not found")
    course_ids = _lecturer_course_ids(db, lecturer)
    if course.id not in course_ids:
        raise ValueError(f"course {course_code} is not in the lecturer's workload")
    student = db.execute(select(Student).where(Student.student_id == student_id)).scalar_one_or_none()
    if student is None:
        raise ValueError(f"student {student_id} not found")
    enrolled = db.execute(
        select(Enrollment).where(Enrollment.student_id == student.id, Enrollment.course_id == course.id)
    ).scalar_one_or_none()
    if enrolled is None:
        raise ValueError(f"student {student_id} is not enrolled in {course_code}")

    approval = ApprovalRequest(
        intent="intervention",
        user_id=actor_user_id or lecturer.user_id,
        payload={
            "action": "intervention",
            "student_id": student.id,
            "student_label": student_id,
            "course_code": course_code,
            "course_title": course.title,
            "plan_text": plan_text,
            "proposed_by": lecturer.staff_id,
            "proposed_at": date.today().isoformat(),
        },
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    record_event(
        db,
        actor=lecturer.staff_id,
        action="intervention_proposed",
        entity_type="approval_request",
        entity_id=approval.id,
        approval_id=approval.id,
        payload={"student_id": student_id, "course_code": course_code, "plan": plan_text[:200]},
    )
    return {"approval_id": approval.id, "status": approval.status, "message": "Intervention proposal created."}


def list_interventions(db: Session, lecturer: Lecturer, *, actor_user_id: str | None = None) -> list[dict]:
    requests = db.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.intent == "intervention", ApprovalRequest.user_id == (actor_user_id or lecturer.user_id))
        .order_by(ApprovalRequest.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": a.id,
            "status": a.status,
            "student_id": a.payload.get("student_label", a.payload.get("student_id", "")),
            "course_code": a.payload.get("course_code", ""),
            "plan_text": a.payload.get("plan_text", ""),
            "created_at": a.created_at.isoformat(),
        }
        for a in requests
    ]


def get_copilot_status(db: Session, lecturer: Lecturer, user: User) -> dict:
    """Per-stage snapshot of the Faculty -> Copilot -> Data -> Analysis ->
    Recommendation -> Approval -> Execute -> Audit Log pipeline."""
    profile = get_profile(db, lecturer)
    rows = list(_course_rows(db, _lecturer_course_ids(db, lecturer)))
    course_codes = {r["course_code"] for r in rows}
    students = {r["student_id"] for r in rows}
    courses_with_data = sum(1 for r in rows if r.get("marks") is not None)

    from app.services.faculty_intelligence import get_intervention_recommendations

    recommendations = len(get_intervention_recommendations(db, lecturer))

    pending = db.execute(
        select(func.count())
        .select_from(ApprovalRequest)
        .where(
            ApprovalRequest.intent == "intervention",
            ApprovalRequest.user_id == user.id,
            ApprovalRequest.status == "pending",
        )
    ).scalar_one()

    executed = 0
    if course_codes:
        executed = db.execute(
            select(func.count())
            .select_from(InterventionPlan)
            .where(InterventionPlan.course_code.in_(course_codes))
        ).scalar_one()

    actors = (user.username, lecturer.staff_id)
    approval_ids = tuple(
        db.execute(
            select(ApprovalRequest.id).where(
                ApprovalRequest.intent == "intervention", ApprovalRequest.user_id == user.id
            )
        ).scalars().all()
    )
    if approval_ids:
        audit_count = db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.actor.in_(actors) | AuditLog.approval_id.in_(approval_ids)
            )
        ).scalar_one()
    else:
        audit_count = db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor.in_(actors))
        ).scalar_one()

    stages = [
        {"key": "faculty", "label": "Faculty", "value": profile["staff_id"], "active": True},
        {"key": "copilot", "label": "Faculty Copilot", "value": profile["course_count"], "active": True},
        {"key": "data", "label": "Course + Student + Curriculum Data", "value": len(students), "active": True},
        {"key": "analysis", "label": "AI Analysis", "value": courses_with_data, "active": True},
        {"key": "recommendation", "label": "Recommendation", "value": recommendations, "active": True},
        {"key": "approval", "label": "Faculty Approval", "value": pending, "active": True},
        {"key": "execute", "label": "Execute Action", "value": executed, "active": True},
        {"key": "audit", "label": "Audit Log", "value": audit_count, "active": True},
    ]
    return {"staff_id": profile["staff_id"], "stages": stages}


def get_my_audit_log(db: Session, lecturer: Lecturer, user: User, limit: int = 50, offset: int = 0) -> dict:
    """Recent audit entries attributable to the acting user (actor username or
    the linked staff id), newest first."""
    actors = (user.username, lecturer.staff_id)
    approval_ids = tuple(
        db.execute(
            select(ApprovalRequest.id).where(
                ApprovalRequest.intent == "intervention", ApprovalRequest.user_id == user.id
            )
        ).scalars().all()
    )
    where = AuditLog.actor.in_(actors)
    if approval_ids:
        where = where | AuditLog.approval_id.in_(approval_ids)
    total = db.execute(select(func.count()).select_from(AuditLog).where(where)).scalar_one()
    entries = db.execute(
        select(AuditLog)
        .where(where)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return {
        "staff_id": lecturer.staff_id,
        "total": total,
        "entries": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "approval_id": e.approval_id,
                "payload": e.payload or {},
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
    }
