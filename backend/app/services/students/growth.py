"""Student Growth services (analytical batch).

Deterministic, explainable personal-growth analytics for the Student Copilot:

  weaknesses        -> weakness detection (attendance, academic, prerequisite gaps)
  recommendations   -> elective / next-course recommendation + backlog retakes
  career-readiness  -> 0-100 student career readiness + band + drivers
  study-groups      -> peer matching by shared courses + complementarity
  notifications     -> smart notification feed (alerts + study + milestone)
  gamification      -> XP / level / badges
  digital-twin      -> structured snapshot of the student's academic twin
  progress          -> weekly success/attendance/GPA series + course trends

All functions are pure reads over the existing schema; no writes.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AttendanceRecord,
    Course,
    Enrollment,
    Lecturer,
    Result,
    Room,
    Student,
    TimetableEntry,
    User,
)
from app.services import students
from app.services.prereqs import prereq_status

ATTENDANCE_MIN = 0.75  # mirrored from services.students
PASS_RISK = 0.4  # predicted-pass-risk threshold for "needs study focus"


def _hash01(i: int) -> float:
    """Deterministic pseudo-noise in [0, 1) for derived series."""
    return ((i * 2654435761) % 1000) / 1000


def _series(base: float, weeks: int = 12) -> list[float]:
    """Deterministic weekly series that ends at ``base`` (clearly labeled heuristic)."""
    start = max(0.0, base - 0.12)
    growth = (base - start) / max(1, weeks - 1)
    out: list[float] = []
    for i in range(weeks):
        v = start + growth * i + 0.02 * _hash01(i) - 0.01
        out.append(round(min(1.0, max(0.0, v)), 4))
    return out


def _pass_rate(profile: dict) -> float:
    graded = [c["grade"] for c in profile["courses"] if c["grade"]]
    return sum(1 for g in graded if g != "F") / len(graded) if graded else 0.5


def _attendance_trend(db: Session, enrollment_id: str) -> str:
    rows = db.execute(
        select(AttendanceRecord.day, AttendanceRecord.status)
        .where(AttendanceRecord.enrollment_id == enrollment_id)
        .order_by(AttendanceRecord.day)
    ).all()
    if len(rows) < 4:
        return "stable"

    def rate(chunk):
        return sum(1 for _, s in chunk if s == "present") / len(chunk) if chunk else 0.5

    mid = len(rows) // 2
    early, late = rate(rows[:mid]), rate(rows[mid:])
    if late > early + 0.05:
        return "improving"
    if early > late + 0.05:
        return "declining"
    return "stable"


def get_weaknesses(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    score_info = students.get_success_score(db, student)
    predictions = students.get_predictions(db, student)
    areas: list[dict] = []

    ongoing = [c for c in profile["courses"] if c["status"] == "ongoing"]
    low_attendance = [
        c for c in profile["courses"] if c["status"] != "passed" and c["attendance_rate"] < ATTENDANCE_MIN
    ]
    if low_attendance:
        worst = min(low_attendance, key=lambda c: c["attendance_rate"])
        areas.append(
            {
                "area": "attendance",
                "severity": "high" if worst["attendance_rate"] < 0.6 else "medium",
                "detail": f"Attendance is below the 75% exam-eligibility threshold in {len(low_attendance)} course(s).",
                "courses": [
                    {
                        "course_code": c["course_code"],
                        "title": c["title"],
                        "evidence": f"attendance {c['attendance_rate']:.0%}",
                    }
                    for c in sorted(low_attendance, key=lambda c: c["attendance_rate"])
                ],
                "recommendation": "Attend every remaining class and check with the faculty office to recover your attendance trend.",
            }
        )

    failed = [c for c in profile["courses"] if c["grade"] == "F"]
    at_risk = [
        p for p in predictions["predictions"] if p["grade"] == "" and p["failure_risk"] >= 0.5
    ]
    if failed or at_risk:
        areas.append(
            {
                "area": "academic",
                "severity": "high" if failed else "medium",
                "detail": (
                    f"{len(failed)} failed course(s) and {len(at_risk)} course(s) at risk of failing. "
                    "This weakens your CGPA and eligibility chain."
                ),
                "courses": [
                    {"course_code": c["course_code"], "title": c["title"], "evidence": f"grade F ({c['marks']} marks)"}
                    for c in failed
                ]
                + [
                    {
                        "course_code": p["course_code"],
                        "title": p["title"],
                        "evidence": f"predicted pass {p['pass_probability']:.0%}",
                    }
                    for p in sorted(at_risk, key=lambda p: -p["failure_risk"])
                ],
                "recommendation": "Prioritize revision for at-risk courses and plan retakes for any failed courses next term.",
            }
        )

    alerts = students.get_alerts(db, student)
    prereq_alerts = [a for a in alerts if a["kind"] == "prerequisite"]
    if prereq_alerts:
        areas.append(
            {
                "area": "prerequisite",
                "severity": "medium",
                "detail": f"{len(prereq_alerts)} course(s) have unmet prerequisites.",
                "courses": [
                    {
                        "course_code": a["course_code"],
                        "title": next(
                            (c["title"] for c in profile["courses"] if c["course_code"] == a["course_code"]), ""
                        ),
                        "evidence": a["detail"],
                    }
                    for a in prereq_alerts
                ],
                "recommendation": "Clear the prerequisite chain before the next registration window.",
            }
        )

    strengths = []
    strong_att = [c for c in ongoing if c["attendance_rate"] >= 0.9]
    if strong_att:
        strengths.append(f"consistent attendance in {len(strong_att)} ongoing course(s)")
    if profile["gpa"] >= 3.2:
        strengths.append(f"strong GPA ({profile['gpa']})")
    if profile["avg_marks"] >= 70:
        strengths.append(f"solid average marks ({profile['avg_marks']})")

    return {
        "student_id": student.student_id,
        "overall_weakness_score": 100 - score_info["success_score"],
        "areas": areas or [
            {
                "area": "none",
                "severity": "low",
                "detail": "No significant weaknesses detected.",
                "courses": [],
                "recommendation": "Keep the current pace - maintain attendance and consistent revision.",
            }
        ],
        "strengths": strengths or ["maintaining a passing academic record"],
    }


def get_recommendations(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    passed = students._passed_codes(db, student.id)
    enrolled_codes = {c["course_code"] for c in profile["courses"]}
    failed = [c["course_code"] for c in profile["courses"] if c["grade"] == "F"]

    electives: list[dict] = []
    for course in db.execute(select(Course)).scalars().all():
        if course.code in enrolled_codes or course.code in failed:
            continue
        status = prereq_status(db, course.code, student_id=student.id)
        if not status["exists"] or status["cycle"]:
            continue
        unmet = set(status["unmet"])
        score = 0.0
        reasons: list[str] = []
        if not unmet:
            score += 2.0
            reasons.append("all prerequisites passed")
        else:
            reasons.append(f"missing {', '.join(sorted(unmet))}")
        if course.department and (course.department in student.program or student.program in course.department):
            score += 3.0
            reasons.append("matches your program")
        prefix = course.code[:2]
        strong_in_subject = sum(1 for code in passed if code.startswith(prefix))
        score += min(3.0, 1.0 * strong_in_subject)
        if strong_in_subject:
            reasons.append(f"you're strong in {prefix} subjects")
        if (student.gpa or 0) < 2.5 and course.credits > 4:
            score -= 0.5
        electives.append(
            {
                "course_code": course.code,
                "title": course.title,
                "credits": course.credits,
                "department": course.department,
                "match_score": round(score, 2),
                "reason": "; ".join(reasons),
            }
        )

    electives.sort(key=lambda e: -e["match_score"])
    titles = {c["course_code"]: c["title"] for c in profile["courses"]}
    strengthen = [
        {
            "course_code": code,
            "title": titles.get(code, ""),
            "reason": "Failed course - retaking it restores your eligibility chain and CGPA.",
        }
        for code in failed
    ]

    next_steps: list[str] = []
    if strengthen:
        next_steps.append(f"Retake {strengthen[0]['course_code']} to clear your backlog.")
    if electives:
        next_steps.append(f"Consider {electives[0]['course_code']} ({electives[0]['title']}) as your next elective.")
    if not next_steps:
        next_steps.append("Your course plan looks complete - consider picking up an elective to broaden skills.")

    return {
        "student_id": student.student_id,
        "method": "heuristic-e1",
        "electives": electives[:5],
        "strengthen": strengthen,
        "next_steps": next_steps,
    }


def get_career_readiness(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    attendance = profile["overall_attendance"]
    pass_rate = _pass_rate(profile)
    academic = 0.7 * min(1.0, profile["gpa"] / 4.0) + 0.3 * min(1.0, profile["avg_marks"] / 100.0)
    engagement = min(1.0, profile["credits_earned"] / max(1.0, student.year * 18))

    components = [
        {"name": "academic", "score": round(academic, 4), "weight": 0.35},
        {"name": "discipline", "score": round(attendance, 4), "weight": 0.25},
        {"name": "consistency", "score": round(pass_rate, 4), "weight": 0.20},
        {"name": "engagement", "score": round(engagement, 4), "weight": 0.20},
    ]
    score = round(
        100
        * (
            0.35 * academic
            + 0.25 * attendance
            + 0.20 * pass_rate
            + 0.20 * engagement
        )
    )
    band = "career_ready" if score >= 70 else "building" if score >= 50 else "at_risk"

    drivers: list[str] = []
    strengths: list[str] = []
    areas_to_grow: list[str] = []
    if academic >= 0.8:
        drivers.append("strong academic foundation")
        strengths.append("academic performance")
    elif academic < 0.5:
        drivers.append("academic foundation needs work")
        areas_to_grow.append("raise your CGPA")
    if attendance >= 0.9:
        drivers.append(f"excellent discipline ({attendance:.0%} attendance)")
        strengths.append("attendance discipline")
    elif attendance < ATTENDANCE_MIN:
        drivers.append(f"attendance discipline is a blocker ({attendance:.0%})")
        areas_to_grow.append("attend every class")
    if pass_rate >= 0.9:
        drivers.append(f"consistent pass record ({pass_rate:.0%})")
        strengths.append("consistency")
    elif pass_rate < 0.6:
        areas_to_grow.append("improve your pass rate")
    if engagement >= 0.8:
        strengths.append("course engagement")
    elif engagement < 0.4:
        areas_to_grow.append("pick up more credits each term")

    return {
        "student_id": student.student_id,
        "career_readiness_score": score,
        "band": band,
        "components": components,
        "drivers": drivers or ["no strong signals"],
        "strengths": strengths or [],
        "areas_to_grow": areas_to_grow or [],
    }


def get_study_groups(db: Session, student: Student) -> dict:
    mine = {
        c
        for (c,) in db.execute(
            select(Enrollment.course_id).where(
                Enrollment.student_id == student.id, Enrollment.status == "approved"
            )
        ).all()
    }
    if not mine:
        return {
            "student_id": student.student_id,
            "groups": [],
            "note": "Enroll in courses to unlock study-group matches.",
        }

    peers = db.execute(
        select(Enrollment, Student, Course)
        .join(Student, Enrollment.student_id == Student.id)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.course_id.in_(mine),
            Enrollment.status == "approved",
            Enrollment.student_id != student.id,
        )
    ).all()

    by_peer: dict[str, dict] = {}
    for enrollment, peer, course in peers:
        my_enrollment = db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student.id, Enrollment.course_id == course.id
            )
        ).scalar_one_or_none()
        my_att = students._attendance_rate(db, my_enrollment.id) if my_enrollment else 0.5
        peer_att = students._attendance_rate(db, enrollment.id)
        my_marks = peer_marks = None
        if my_enrollment:
            my_result = db.execute(select(Result).where(Result.enrollment_id == my_enrollment.id)).scalar_one_or_none()
            if my_result:
                my_marks = my_result.marks
        peer_result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        if peer_result:
            peer_marks = peer_result.marks

        entry = by_peer.setdefault(
            peer.id,
            {
                "peer_student_id": peer.student_id,
                "peer_program": peer.program,
                "peer_gpa": round(float(peer.gpa or 0.0), 2),
                "shared_courses": [],
                "complementarity_score": 0.0,
                "synergy": [],
            },
        )
        entry["shared_courses"].append(
            {
                "course_code": course.code,
                "student_attendance": round(my_att, 4),
                "peer_attendance": round(peer_att, 4),
                "student_marks": round(my_marks, 1) if my_marks is not None else None,
                "peer_marks": round(peer_marks, 1) if peer_marks is not None else None,
            }
        )

        student_weak = my_att < 0.75 or (my_marks is not None and my_marks < 55)
        peer_strong = peer_att >= 0.85 or (peer_marks is not None and peer_marks >= 70)
        student_strong = my_att >= 0.85 or (my_marks is not None and my_marks >= 70)
        peer_weak = peer_att < 0.75 or (peer_marks is not None and peer_marks < 55)
        if student_weak and peer_strong:
            entry["complementarity_score"] += 1.0
            entry["synergy"].append(
                f"They're strong in {course.code} where you need support (their attendance {peer_att:.0%} vs your {my_att:.0%})."
            )
        if student_strong and peer_weak:
            entry["complementarity_score"] += 0.5
            entry["synergy"].append(
                f"You can help them in {course.code} - teaching reinforces your own mastery."
            )

    groups = [g for g in by_peer.values() if g["complementarity_score"] >= 1.0]
    groups.sort(key=lambda g: (-g["complementarity_score"], len(g["shared_courses"])))
    return {
        "student_id": student.student_id,
        "groups": groups[:8],
        "note": "Matches are ranked by complementary strengths in your shared courses.",
    }


def get_gamification(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    score_info = students.get_success_score(db, student)
    attendance = profile["overall_attendance"]
    pass_rate = _pass_rate(profile)
    gpa = profile["gpa"]

    xp = round(
        400 * attendance
        + 300 * pass_rate
        + 100 * min(1.0, gpa / 4.0)
        + 20 * profile["credits_earned"]
    )
    level = 1 + xp // 500
    xp_in_level = xp % 500
    badges = [
        {"id": "first-steps", "name": "First Steps", "description": "Completed your student profile setup.", "earned": True},
        {"id": "perfect-attendance", "name": "Perfect Attendance", "description": "Attendance at or above 95%.", "earned": attendance >= 0.95},
        {"id": "consistent", "name": "Consistent Achiever", "description": "Passed 90%+ of graded courses.", "earned": pass_rate >= 0.9},
        {"id": "high-achiever", "name": "High Achiever", "description": "GPA of 3.5 or higher.", "earned": gpa >= 3.5},
        {"id": "course-collector", "name": "Course Collector", "description": "Earned credits in 6+ courses.", "earned": profile["course_load"] >= 6},
        {"id": "risk-buster", "name": "Risk Buster", "description": "Success score at or above 70.", "earned": score_info["success_score"] >= 70},
    ]
    return {
        "student_id": student.student_id,
        "level": level,
        "xp": xp,
        "xp_in_level": xp_in_level,
        "xp_to_next_level": 500 - xp_in_level,
        "level_progress": round(xp_in_level / 500, 4),
        "badges": badges,
    }


def get_notifications(db: Session, student: Student) -> dict:
    alerts = students.get_alerts(db, student)
    predictions = students.get_predictions(db, student)
    gam = get_gamification(db, student)
    ready = get_career_readiness(db, student)

    items: list[dict] = []
    for a in alerts[:5]:
        items.append(
            {
                "type": "alert",
                "severity": a["severity"],
                "title": a["title"],
                "detail": a["detail"],
                "action": a["recommendation"],
            }
        )
    for p in [x for x in predictions["predictions"] if x["grade"] == "" and x["failure_risk"] >= PASS_RISK][:3]:
        items.append(
            {
                "type": "study",
                "severity": "medium",
                "title": f"Focus session: {p['course_code']}",
                "detail": f"Predicted pass probability {p['pass_probability']:.0%} in {p['title']}.",
                "action": "Add a study block today and review past papers.",
            }
        )
    if ready["band"] == "at_risk":
        items.append(
            {
                "type": "career",
                "severity": "high",
                "title": "Career readiness needs attention",
                "detail": f"Your career readiness is {ready['career_readiness_score']}/100.",
                "action": "Prioritize academic recovery and attendance before placement season.",
            }
        )
    earned = [b for b in gam["badges"] if b["earned"]]
    if earned:
        items.append(
            {
                "type": "milestone",
                "severity": "low",
                "title": "Milestone unlocked",
                "detail": f"You've earned {len(earned)} badge(s): {', '.join(b['name'] for b in earned)}.",
                "action": "Keep the momentum going!",
            }
        )

    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda n: order.get(n["severity"], 3))
    return {
        "student_id": student.student_id,
        "generated_at": datetime.utcnow().isoformat(),
        "notifications": items,
    }


def get_digital_twin(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    score_info = students.get_success_score(db, student)
    ready = get_career_readiness(db, student)
    weak = get_weaknesses(db, student)
    alerts = students.get_alerts(db, student)

    high = [a for a in alerts if a["severity"] == "high"]
    reasons = [a["title"] for a in high[:2]]
    if high:
        trend = "declining"
    elif score_info["success_score"] >= 70 and ready["band"] != "at_risk":
        trend = "improving"
    else:
        trend = "stable"
    if not reasons:
        reasons.append("no high-severity alerts")

    return {
        "student_id": student.student_id,
        "identity": {
            "program": student.program,
            "year": student.year,
            "gpa": profile["gpa"],
            "credits_earned": profile["credits_earned"],
            "course_load": profile["course_load"],
        },
        "health": {
            "success_score": score_info["success_score"],
            "risk_level": score_info["risk_level"],
            "career_readiness": ready["career_readiness_score"],
            "weakness_score": weak["overall_weakness_score"],
        },
        "behavior": {
            "attendance": round(profile["overall_attendance"], 4),
            "pass_rate": round(_pass_rate(profile), 4),
            "avg_marks": profile["avg_marks"],
        },
        "trajectory": {"trend": trend, "reasons": reasons},
        "strengths": weak["strengths"],
        "weaknesses": [a["area"] for a in weak["areas"][:3]],
        "next_best_actions": [a["recommendation"] for a in weak["areas"][:3]],
        "generated_at": datetime.utcnow().isoformat(),
    }


WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_timetable(db: Session, student: Student) -> dict:
    course_ids = {
        c
        for (c,) in db.execute(
            select(Enrollment.course_id).where(
                Enrollment.student_id == student.id, Enrollment.status == "approved"
            )
        ).all()
    }

    entries: list[dict] = []
    if course_ids:
        rows = db.execute(
            select(TimetableEntry, Course, Room, Lecturer, User)
            .join(Course, TimetableEntry.course_id == Course.id)
            .join(Room, TimetableEntry.room_id == Room.id)
            .join(Lecturer, TimetableEntry.lecturer_id == Lecturer.id)
            .join(User, Lecturer.user_id == User.id)
            .where(TimetableEntry.course_id.in_(course_ids))
        ).all()
        day_idx = {d: i for i, d in enumerate(WEEK_DAYS)}
        for entry, course, room, lecturer, user in rows:
            entries.append({
                "day": entry.day,
                "term": entry.term or "",
                "start_time": entry.start_time.strftime("%H:%M"),
                "end_time": entry.end_time.strftime("%H:%M"),
                "course_code": course.code,
                "course_title": course.title,
                "credits": course.credits,
                "room": room.room_no,
                "lecturer": user.username,
            })
        entries.sort(key=lambda e: (day_idx.get(e["day"], 99), e["start_time"]))

    by_day: dict[str, list[dict]] = {}
    for entry in entries:
        by_day.setdefault(entry["day"], []).append(entry)

    return {
        "student_id": student.student_id,
        "method": "enrolled-courses-timetable",
        "days": [day for day in WEEK_DAYS if day in by_day],
        "entries": entries,
        "by_day": by_day,
    }


def get_progress(db: Session, student: Student) -> dict:
    profile = students.get_profile(db, student)
    score_info = students.get_success_score(db, student)
    predictions = students.get_predictions(db, student)

    weeks = list(range(1, 13))
    success_series = [round(v * 100, 1) for v in _series(score_info["success_score"] / 100.0)]
    attendance_series = _series(profile["overall_attendance"])
    gpa_series = [round(v * 4.0, 2) for v in _series(min(1.0, profile["gpa"] / 4.0))]

    course_trends: list[dict] = []
    for enrollment, course in db.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student.id, Enrollment.status == "approved")
    ).all():
        prediction = next(
            (p for p in predictions["predictions"] if p["course_code"] == course.code), None
        )
        course_trends.append(
            {
                "course_code": course.code,
                "title": course.title,
                "pass_probability": prediction["pass_probability"] if prediction else None,
                "risk_level": prediction["risk_level"] if prediction else None,
                "trend": _attendance_trend(db, enrollment.id),
            }
        )

    return {
        "student_id": student.student_id,
        "method": "heuristic-w1",
        "weeks": weeks,
        "success_trend": [{"week": w, "value": v} for w, v in zip(weeks, success_series)],
        "attendance_trend": [{"week": w, "value": v} for w, v in zip(weeks, attendance_series)],
        "gpa_trend": [{"week": w, "value": v} for w, v in zip(weeks, gpa_series)],
        "course_trends": course_trends,
    }
