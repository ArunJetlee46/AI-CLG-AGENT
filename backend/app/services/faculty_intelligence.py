"""Faculty Copilot intelligence services (deterministic, explainable batch).

Built on top of the existing faculty analytics:
  learning-outcomes        -> per-course outcome mastery from marks/attendance
  remedial-plan            -> step-by-step remedial plan for an at-risk student
  high-performers          -> ranked high performers with reasons
  research-recommendations -> students recommended for research supervision
  schedule                 -> weekly teaching load vs capacity
  course-report            -> single automated report document per course
  digital-twin             -> teaching snapshot with strengths/weaknesses
  similarity               -> pairwise text similarity (plagiarism screen)
  intervention-rec         -> automated remedial recommendations per at-risk row

All functions are pure reads on the database (except similarity, which reads
the submitted texts) and never require the LLM.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Course, Enrollment, Lecturer, Student
from app.services.faculty import (
    _course_rows,
    _dropout_proba,
    _lecturer_course_ids,
    _risk_band,
    get_course_health,
    get_profile,
)

ATTENDANCE_MIN = 0.75
HIGH_MARK = 75.0
LOW_MARK = 50.0

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _grouped_rows(db: Session, lecturer: Lecturer) -> dict[str, list[dict]]:
    rows = _course_rows(db, _lecturer_course_ids(db, lecturer))
    by_course: dict[str, list[dict]] = {}
    for row in rows:
        by_course.setdefault(row["course_code"], []).append(row)
    return by_course


def _student_profile_summary(row: dict) -> float:
    """0-100 composite for a single enrollment row."""
    marks = (row["marks"] or 0.0) / 100.0
    return 100.0 * (0.4 * min(1.0, row["gpa"] / 4.0) + 0.3 * min(1.0, marks) + 0.3 * row["attendance_rate"])


def _band(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# 1. learning outcome analytics
# ---------------------------------------------------------------------------


def get_learning_outcomes(db: Session, lecturer: Lecturer) -> dict:
    """Per-course learning outcome mastery derived from the result distribution
    and attendance. Outcome areas mirror the course's stated objectives."""
    by_course = _grouped_rows(db, lecturer)
    outcomes: list[dict] = []
    for code in sorted(by_course):
        rows = by_course[code]
        marks = [r["marks"] for r in rows if r["marks"] is not None]
        attendance = sum(r["attendance_rate"] for r in rows) / len(rows)
        dist = {"high": 0, "medium": 0, "low": 0}
        for m in marks:
            band = "high" if m >= HIGH_MARK else ("medium" if m >= LOW_MARK else "low")
            dist[band] += 1
        mastery = sum(marks) / len(marks) if marks else 0.0
        outcome_rows = [
            {
                "area": "core concepts",
                "mastery": round(mastery, 1),
                "band": _band(mastery),
                "detail": f"Average marks {mastery:.1f}/100 across {len(marks)} graded submissions.",
            },
            {
                "area": "application",
                "mastery": round(mastery * 0.9 + (100 - mastery) * 0.1, 1),
                "band": _band(mastery),
                "detail": "Application weighted slightly below concept mastery; drives project and exam readiness.",
            },
            {
                "area": "engagement",
                "mastery": round(attendance * 100, 1),
                "band": _band(attendance * 100),
                "detail": f"Average attendance {attendance:.0%} across {len(rows)} enrolled students.",
            },
        ]
        outcomes.append(
            {
                "course_code": code,
                "title": rows[0]["course_title"],
                "enrolled": len(rows),
                "distribution": dist,
                "outcomes": outcome_rows,
                "weakest_area": min(outcome_rows, key=lambda o: o["mastery"])["area"],
            }
        )
    return {"staff_id": lecturer.staff_id, "courses": outcomes}


# ---------------------------------------------------------------------------
# 2. remedial plan generator
# ---------------------------------------------------------------------------


def get_remedial_plan(db: Session, lecturer: Lecturer, course_code: str, student_id: str) -> dict:
    rows = [r for r in _course_rows(db, _lecturer_course_ids(db, lecturer))
            if r["course_code"] == course_code and r["student_id"] == student_id]
    if not rows:
        return {"exists": False, "detail": "Student is not enrolled in this course under your workload."}
    row = rows[0]
    proba = _dropout_proba(row["gpa"], row["attendance_rate"], row["marks"] or 0.0)

    steps: list[dict] = []
    if row["attendance_rate"] < ATTENDANCE_MIN:
        steps.append({
            "kind": "attendance",
            "priority": "high",
            "action": "Join the attendance recovery program - attend every class for the next two weeks to rebuild the trend.",
            "metric": f"raise attendance from {row['attendance_rate']:.0%} to at least 75%",
        })
    if row["gpa"] < 2.5:
        steps.append({
            "kind": "academic",
            "priority": "high",
            "action": "Set up weekly one-on-one mentoring sessions to rebuild fundamentals.",
            "metric": f"raise GPA from {row['gpa']} toward 2.5+",
        })
    if row["marks"] is not None and row["marks"] < LOW_MARK:
        steps.append({
            "kind": "assessment",
            "priority": "high" if row["marks"] < 40 else "medium",
            "action": "Complete a targeted practice set on the low-mark modules before the next assessment.",
            "metric": f"raise assessment marks from {row['marks']} toward 50+",
        })
    if row["attendance_trend"] < -0.02:
        steps.append({
            "kind": "monitoring",
            "priority": "medium",
            "action": "Set a biweekly check-in to review the attendance trend in this course.",
            "metric": "stabilise the declining attendance trend",
        })
    if not steps:
        steps.append({
            "kind": "maintain",
            "priority": "low",
            "action": "Maintain current performance and take on stretch problems to solidify the subject.",
            "metric": "sustain current standing",
        })

    return {
        "exists": True,
        "student_id": student_id,
        "course_code": course_code,
        "course_title": row["course_title"],
        "risk_level": _risk_band(proba),
        "probability": round(proba, 4),
        "profile": {
            "gpa": row["gpa"],
            "attendance_rate": row["attendance_rate"],
            "marks": row["marks"],
            "grade": row["grade"],
        },
        "steps": steps,
        "review_after_days": 14,
    }


# ---------------------------------------------------------------------------
# 3. high performer detection
# ---------------------------------------------------------------------------


def get_high_performers(db: Session, lecturer: Lecturer, limit: int = 10) -> list[dict]:
    rows = _course_rows(db, _lecturer_course_ids(db, lecturer))
    by_student: dict[str, list[dict]] = {}
    for row in rows:
        by_student.setdefault(row["student_id"], []).append(row)

    scored: list[dict] = []
    for student_id, group in by_student.items():
        gpa = group[0]["gpa"]
        marks = [r["marks"] for r in group if r["marks"] is not None]
        attendance = sum(r["attendance_rate"] for r in group) / len(group)
        score = _student_profile_summary(group[0])
        reasons: list[str] = []
        if gpa >= 3.5:
            reasons.append(f"GPA {gpa} is exceptional")
        if marks and sum(marks) / len(marks) >= 80:
            reasons.append(f"average marks {sum(marks) / len(marks):.0f}")
        if attendance >= 0.9:
            reasons.append(f"attendance {attendance:.0%}")
        if all(r["grade"] not in ("", "F") and r["grade"] != "F" for r in group):
            reasons.append("no failures")
        scored.append(
            {
                "student_id": student_id,
                "gpa": gpa,
                "attendance_rate": round(attendance, 4),
                "avg_marks": round(sum(marks) / len(marks), 1) if marks else None,
                "courses": [r["course_code"] for r in group],
                "score": round(score, 1),
                "band": _band(score),
                "reasons": reasons or ["consistent across courses"],
            }
        )
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# 4. research student recommendation
# ---------------------------------------------------------------------------


def get_research_recommendations(db: Session, lecturer: Lecturer, limit: int = 8) -> dict:
    high = get_high_performers(db, lecturer, limit=100)
    candidates: list[dict] = []
    for s in high:
        if s["gpa"] < 3.2:
            continue
        if s["avg_marks"] is not None and s["avg_marks"] < 75:
            continue
        area = _infer_research_area(s)
        candidates.append(
            {
                "student_id": s["student_id"],
                "gpa": s["gpa"],
                "avg_marks": s["avg_marks"],
                "score": s["score"],
                "courses": s["courses"],
                "suggested_area": area,
                "rationale": (
                    f"GPA {s['gpa']} with strong, consistent results in {', '.join(s['courses'][:3])} "
                    "indicates readiness for supervised research."
                ),
            }
        )
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return {"staff_id": lecturer.staff_id, "candidates": candidates[:limit]}


def _infer_research_area(performer: dict) -> str:
    text = " ".join(performer["courses"]).lower()
    for keyword, area in (
        ("data", "Data Science"),
        ("ml", "Machine Learning"),
        ("ai", "Artificial Intelligence"),
        ("python", "Software Engineering"),
        ("java", "Software Engineering"),
        ("web", "Web Technologies"),
        ("network", "Networks"),
        ("database", "Databases"),
        ("math", "Applied Mathematics"),
    ):
        if keyword in text:
            return area
    return "Core Computer Science"


# ---------------------------------------------------------------------------
# 5. faculty smart schedule
# ---------------------------------------------------------------------------


def get_schedule(db: Session, lecturer: Lecturer) -> dict:
    from app.models.entities import TimetableEntry

    entries = db.execute(
        select(TimetableEntry).where(TimetableEntry.lecturer_id == lecturer.id)
    ).scalars().all()

    day_order = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    by_day: dict[str, list[dict]] = {}
    total_hours = 0.0
    for entry in entries:
        duration = (entry.end_time.hour * 60 + entry.end_time.minute
                    - (entry.start_time.hour * 60 + entry.start_time.minute)) / 60
        total_hours += max(0.0, duration)
        course = db.execute(select(Course).where(Course.id == entry.course_id)).scalar_one_or_none()
        day = (entry.day or "MON").upper()
        by_day.setdefault(day, []).append(
            {
                "course_code": course.code if course else "",
                "title": course.title if course else "",
                "start": entry.start_time.strftime("%H:%M"),
                "end": entry.end_time.strftime("%H:%M"),
                "hours": round(max(0.0, duration), 1),
            }
        )
    days = sorted(by_day, key=lambda d: day_order.get(d, 9))
    profile = get_profile(db, lecturer)
    max_hours = profile["max_hours"] or lecturer.max_hours
    utilization = round(min(100.0, 100.0 * total_hours / max_hours), 1) if max_hours else 0.0
    return {
        "staff_id": lecturer.staff_id,
        "total_hours": round(total_hours, 1),
        "max_hours": max_hours,
        "utilization": utilization,
        "overloaded": total_hours > max_hours,
        "sessions": len(entries),
        "days": [{"day": d, "slots": by_day[d]} for d in days],
        "advisory": "Teaching load exceeds the weekly cap - request relief or merge sessions." if total_hours > max_hours
        else ("Load is within the weekly cap. Reserve one block for office hours." if utilization >= 80
              else "Load is light - use free time for research and material preparation."),
    }


# ---------------------------------------------------------------------------
# 6. automated course reports
# ---------------------------------------------------------------------------


def get_course_report(db: Session, lecturer: Lecturer, course_code: str) -> dict:
    from app.services.faculty import get_course_health

    health = get_course_health(db, lecturer, course_code)
    if not health.get("exists") or not health.get("authorized"):
        return {"course_code": course_code, "exists": health.get("exists", False),
                "authorized": health.get("authorized", False)}
    rows = [r for r in _course_rows(db, _lecturer_course_ids(db, lecturer)) if r["course_code"] == course_code]
    marks = sorted((r["marks"] for r in rows if r["marks"] is not None), reverse=True)
    at_risk = [r for r in get_at_risk_slice(db, lecturer, course_code)]
    attendance = sum(r["attendance_rate"] for r in rows) / len(rows) if rows else 0.0
    pass_rate = health["components"]["pass_rate"]

    distribution = {
        "outstanding": sum(1 for m in marks if m >= 90),
        "good": sum(1 for m in marks if 75 <= m < 90),
        "average": sum(1 for m in marks if 50 <= m < 75),
        "below": sum(1 for m in marks if m < 50),
    }

    narrative = (
        f"{health['course_title']} ({course_code}) is rated {health['band']} with a health score of "
        f"{health['health_score']}/100. {len(rows)} students are enrolled with an average attendance of "
        f"{attendance:.0%} and a pass rate of {pass_rate:.0%}. "
        + (f"{len(at_risk)} students are flagged at-risk and need targeted remedial support. "
           if at_risk else "No students are currently flagged at-risk. ")
        + f"Recommended focus: {health['drivers'][0] if health['drivers'] else 'maintain current momentum'}."
    )

    return {
        "course_code": course_code,
        "course_title": health["course_title"],
        "generated_on": date.today().isoformat(),
        "health_score": health["health_score"],
        "band": health["band"],
        "enrolled": len(rows),
        "attendance": round(attendance, 4),
        "pass_rate": pass_rate,
        "distribution": distribution,
        "top_students": [r["student_id"] for r in sorted(rows, key=lambda r: r["marks"] or 0, reverse=True)[:3]],
        "at_risk_students": [{"student_id": r["student_id"], "risk_level": r["risk_level"]} for r in at_risk[:10]],
        "drivers": health["drivers"],
        "narrative": narrative,
    }


def get_at_risk_slice(db: Session, lecturer: Lecturer, course_code: str) -> list[dict]:
    from app.services.faculty import get_at_risk

    return [r for r in get_at_risk(db, lecturer, limit=500) if r["course_code"] == course_code]


# ---------------------------------------------------------------------------
# 7. faculty digital twin
# ---------------------------------------------------------------------------


def get_faculty_digital_twin(db: Session, lecturer: Lecturer) -> dict:
    profile = get_profile(db, lecturer)
    by_course = _grouped_rows(db, lecturer)
    all_rows = [r for group in by_course.values() for r in group]
    overview_health = [get_course_health(db, lecturer, code) for code in sorted(by_course)]
    avg_health = round(sum(h["health_score"] or 0 for h in overview_health) / len(overview_health), 1) if overview_health else 0.0
    at_risk = [r for r in get_at_risk_slice(db, lecturer, "") if r["risk_level"] == "high"]
    attendance = sum(r["attendance_rate"] for r in all_rows) / len(all_rows) if all_rows else 0.0
    high = get_high_performers(db, lecturer, limit=3)

    strengths: list[str] = []
    if avg_health >= 75:
        strengths.append(f"average course health {avg_health} is healthy")
    if attendance >= 0.85:
        strengths.append(f"strong class attendance ({attendance:.0%})")
    if profile["course_count"] and profile["teaching_hours"] <= (profile["max_hours"] or 20):
        strengths.append("teaching load is within capacity")
    weaknesses: list[str] = []
    if avg_health < 55:
        weaknesses.append(f"average course health {avg_health} is weak")
    if attendance < ATTENDANCE_MIN:
        weaknesses.append(f"class attendance {attendance:.0%} below 75%")
    if at_risk:
        weaknesses.append(f"{len(at_risk)} students at high risk")

    trajectory = "improving" if avg_health >= 70 else ("declining" if avg_health < 55 else "stable")

    return {
        "staff_id": lecturer.staff_id,
        "identity": {
            "department": lecturer.department,
            "courses": profile["course_count"],
            "students": profile["student_count"],
            "teaching_hours": profile["teaching_hours"],
            "max_hours": profile["max_hours"],
        },
        "health": {"avg_course_health": avg_health, "at_risk_count": len(at_risk),
                   "high_performers": len(high), "attendance": round(attendance, 4)},
        "trajectory": {"trend": trajectory, "reasons": strengths + weaknesses or ["stable workload"]},
        "strengths": strengths or ["stable teaching load"],
        "weaknesses": weaknesses or ["no critical flags"],
        "next_best_actions": [
            f"Run a remedial plan for {len(at_risk)} at-risk students." if at_risk else "Schedule a course-health review for the lowest band course.",
            "Prepare a weekly lesson plan for the weakest course.",
        ],
        "generated_at": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# 8. similarity / plagiarism detection
# ---------------------------------------------------------------------------


def _n_grams(text: str, n: int = 4) -> set[str]:
    clean = " ".join(text.lower().split())
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def get_similarity(db: Session, lecturer: Lecturer, submissions: list[dict], threshold: float = 0.35) -> dict:
    """Pairwise character 4-gram Jaccard similarity between submitted texts.
    High scores indicate probable copying; review flagged pairs manually."""
    items: list[dict] = []
    for i, sub in enumerate(submissions):
        text = str(sub.get("text", ""))
        items.append(
            {
                "student_id": str(sub.get("student_id", f"#sub-{i + 1}")),
                "text": text,
                "grams": _n_grams(text) if text else set(),
                "words": len(text.split()),
            }
        )
    pairs: list[dict] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            score = _jaccard(items[i]["grams"], items[j]["grams"])
            if score >= threshold:
                pairs.append(
                    {
                        "student_a": items[i]["student_id"],
                        "student_b": items[j]["student_id"],
                        "similarity": round(score, 4),
                        "flag": "high" if score >= 0.6 else ("medium" if score >= 0.45 else "low"),
                    }
                )
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return {
        "staff_id": lecturer.staff_id,
        "threshold": threshold,
        "submissions": len(items),
        "pairs": pairs,
        "note": "Character 4-gram overlap. High similarity warrants manual review before any action.",
    }


# ---------------------------------------------------------------------------
# 9. automated intervention recommendations
# ---------------------------------------------------------------------------


def get_intervention_recommendations(db: Session, lecturer: Lecturer, limit: int = 20) -> list[dict]:
    rows = _course_rows(db, _lecturer_course_ids(db, lecturer))
    scored: list[dict] = []
    for row in rows:
        proba = _dropout_proba(row["gpa"], row["attendance_rate"], row["marks"] or 0.0)
        if proba < 0.4:
            continue
        actions: list[str] = []
        if row["attendance_rate"] < ATTENDANCE_MIN:
            actions.append("Attendance recovery: mandatory class presence + parent/mentor notification.")
        if row["gpa"] < 2.5:
            actions.append("Academic mentoring: weekly sessions focused on core fundamentals.")
        if row["marks"] is not None and row["marks"] < LOW_MARK:
            actions.append(f"Assessment clinic: rework the low-score modules ({row['marks']}/100).")
        if row["attendance_trend"] < -0.02:
            actions.append("Trend monitoring: biweekly attendance check-ins.")
        if not actions:
            actions.append("Preventive guidance: early tutor check-in before risk grows.")
        scored.append(
            {
                "student_id": row["student_id"],
                "course_code": row["course_code"],
                "course_title": row["course_title"],
                "probability": round(proba, 4),
                "risk_level": _risk_band(proba),
                "recommendation": actions,
                "proposed_action": actions[0],
            }
        )
    scored.sort(key=lambda s: s["probability"], reverse=True)
    return scored[:limit]
