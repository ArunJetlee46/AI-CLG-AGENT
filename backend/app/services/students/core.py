"""Student Copilot services.

Deterministic, explainable student-facing analytics built on the existing ML
and prerequisite layers:

  profile          -> enrolled courses, attendance, grades, credits, CGPA
  success-score    -> 0-100 composite + Low/Medium/High risk band + drivers
  alerts           -> early warnings (attendance, grades, unmet prereqs)
  predictions      -> per-course pass probability + projected CGPA
  advise           -> course eligibility via the prerequisite graph
  today            -> prioritized "what should I do today" plan

The demo `student` account has no Student row; `resolve_student` falls back to
`settings.demo_student_id` (STU00000) so the dashboard works out of the box.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import AttendanceRecord, Course, Enrollment, Result, Student, User
from app.services.prereqs import prereq_status

settings = get_settings()

ATTENDANCE_MIN = 0.75  # KB rule: below 75% -> ineligible to sit the exam
PASS_PROB_BANDS = (0.4, 0.7)  # failure-risk bands (mirror ml.predict)


def resolve_student(db: Session, user: User) -> Student | None:
    """Map an authenticated user to the Student row they own."""
    if user.student is not None:
        return user.student
    linked = db.execute(select(Student).where(Student.student_id == user.username)).scalar_one_or_none()
    if linked is not None:
        return linked
    demo = db.execute(select(Student).where(Student.student_id == settings.demo_student_id)).scalar_one_or_none()
    if demo is not None:
        return demo
    return db.execute(select(Student).order_by(Student.student_id)).scalars().first()


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


def _passed_codes(db: Session, student_id: str) -> set[str]:
    return {
        code
        for (code,) in db.execute(
            select(Course.code)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .join(Result, Result.enrollment_id == Enrollment.id)
            .where(Enrollment.student_id == student_id, Result.grade != "F")
        ).all()
    }


def _courses(db: Session, student: Student) -> list[dict]:
    enrollments = db.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student.id, Enrollment.status == "approved")
        .order_by(Course.code)
    ).all()
    courses: list[dict] = []
    for enrollment, course in enrollments:
        rate = _attendance_rate(db, enrollment.id)
        result = db.execute(select(Result).where(Result.enrollment_id == enrollment.id)).scalar_one_or_none()
        grade = result.grade if result else ""
        status = "failed" if grade == "F" else ("passed" if grade else "ongoing")
        courses.append(
            {
                "course_code": course.code,
                "title": course.title,
                "credits": course.credits,
                "marks": round(result.marks, 1) if result else None,
                "grade": grade,
                "status": status,
                "attendance_rate": round(rate, 4),
            }
        )
    return courses


def get_profile(db: Session, student: Student) -> dict:
    courses = _courses(db, student)
    att_sum = sum(c["attendance_rate"] for c in courses)
    marks = [c["marks"] for c in courses if c["marks"] is not None]
    credits_earned = sum(c["credits"] for c in courses if c["grade"] not in ("", "F"))
    return {
        "student_id": student.student_id,
        "program": student.program,
        "year": student.year,
        "gpa": round(float(student.gpa or 0.0), 2),
        "overall_attendance": round(att_sum / len(courses), 4) if courses else 0.0,
        "avg_marks": round(sum(marks) / len(marks), 1) if marks else 0.0,
        "credits_earned": credits_earned,
        "course_load": len(courses),
        "courses": courses,
    }


def get_success_score(db: Session, student: Student) -> dict:
    profile = get_profile(db, student)
    graded = [c["grade"] for c in profile["courses"] if c["grade"]]
    pass_rate = sum(1 for g in graded if g != "F") / len(graded) if graded else 0.5

    attendance_component = profile["overall_attendance"]
    academic_component = 0.7 * min(1.0, profile["gpa"] / 4.0) + 0.3 * min(1.0, profile["avg_marks"] / 100.0)
    consistency_component = pass_rate
    score = int(round(max(0.0, min(100.0, 100.0 * (
        0.30 * attendance_component + 0.45 * academic_component + 0.25 * consistency_component
    )))))

    if score >= 70:
        risk_level = "low"
    elif score >= 50:
        risk_level = "medium"
    else:
        risk_level = "high"

    drivers = []
    if attendance_component >= 0.85:
        drivers.append(f"attendance is strong ({profile['overall_attendance']:.0%})")
    elif attendance_component < 0.75:
        drivers.append(f"attendance is weak ({profile['overall_attendance']:.0%})")
    if profile["gpa"] >= 3.2:
        drivers.append(f"GPA {profile['gpa']} is strong")
    elif profile["gpa"] < 2.5:
        drivers.append(f"GPA {profile['gpa']} needs attention")
    if consistency_component >= 0.85:
        drivers.append(f"consistent pass record ({pass_rate:.0%} of graded courses)")
    elif consistency_component < 0.6:
        drivers.append(f"low pass rate ({pass_rate:.0%} of graded courses)")

    return {
        "student_id": student.student_id,
        "success_score": score,
        "risk_level": risk_level,
        "components": [
            {"name": "attendance", "score": round(attendance_component, 4), "weight": 0.30},
            {"name": "academic", "score": round(academic_component, 4), "weight": 0.45},
            {"name": "consistency", "score": round(consistency_component, 4), "weight": 0.25},
        ],
        "drivers": drivers or ["no strong drivers"],
    }


def get_alerts(db: Session, student: Student) -> list[dict]:
    courses = _courses(db, student)
    alerts: list[dict] = []
    passed = _passed_codes(db, student.id)

    for c in courses:
        if c["attendance_rate"] < ATTENDANCE_MIN:
            alerts.append(
                {
                    "severity": "high",
                    "kind": "attendance",
                    "course_code": c["course_code"],
                    "title": "Attendance below minimum",
                    "detail": (
                        f"Attendance in {c['course_code']} is {c['attendance_rate']:.0%}, "
                        "below the 75% required to sit the exam."
                    ),
                    "recommendation": "Attend the next classes to recover your attendance trend.",
                }
            )
        if c["grade"] == "F":
            alerts.append(
                {
                    "severity": "high",
                    "kind": "grade",
                    "course_code": c["course_code"],
                    "title": "Failing grade",
                    "detail": f"You have a failing grade (F) in {c['course_code']} ({c['marks']} marks).",
                    "recommendation": "Retake the course or request tutoring through the faculty office.",
                }
            )
        elif c["grade"] == "E":
            alerts.append(
                {
                    "severity": "medium",
                    "kind": "grade",
                    "course_code": c["course_code"],
                    "title": "Borderline grade",
                    "detail": f"{c['course_code']} was passed with a borderline grade (E, {c['marks']} marks).",
                    "recommendation": "Reinforce the material before any retake or advanced course.",
                }
            )
        if c["grade"] != "":
            continue
        status = prereq_status(db, c["course_code"], student_id=student.id)
        unmet = sorted(set(status["unmet"]))
        if status["exists"] and unmet and not status["cycle"]:
            alerts.append(
                {
                    "severity": "medium",
                    "kind": "prerequisite",
                    "course_code": c["course_code"],
                    "title": "Unmet prerequisite",
                    "detail": f"{c['course_code']} requires {', '.join(unmet)} which you have not passed yet.",
                    "recommendation": "Complete the prerequisite courses before registering for the exam.",
                }
            )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(alerts, key=lambda a: severity_order.get(a["severity"], 3))


def get_predictions(db: Session, student: Student) -> dict:
    profile = get_profile(db, student)
    gpa = profile["gpa"]
    rows: list[dict] = []
    for c in profile["courses"]:
        pass_prob = 0.5 * c["attendance_rate"] + 0.5 * min(1.0, gpa / 4.0)
        pass_prob = round(max(0.0, min(1.0, pass_prob)), 4)
        failure_risk = round(1.0 - pass_prob, 4)
        risk_level = (
            "high" if failure_risk >= PASS_PROB_BANDS[1]
            else "medium" if failure_risk >= PASS_PROB_BANDS[0]
            else "low"
        )
        rows.append(
            {
                "course_code": c["course_code"],
                "title": c["title"],
                "credits": c["credits"],
                "grade": c["grade"],
                "status": c["status"],
                "attendance_rate": c["attendance_rate"],
                "pass_probability": pass_prob,
                "failure_risk": failure_risk,
                "risk_level": risk_level,
            }
        )

    ongoing = [r for r in rows if r["grade"] == ""]
    ongoing_mean = sum(r["pass_probability"] for r in ongoing) / len(ongoing) if ongoing else None
    projected_gpa = round(min(4.0, gpa + 0.3 * ((ongoing_mean or 0.7) - 0.7)), 2)

    return {
        "student_id": student.student_id,
        "gpa": gpa,
        "projected_gpa": projected_gpa,
        "method": "heuristic-v1",
        "note": "Pass probability = 0.5*attendance + 0.5*min(1, gpa/4); risk bands >=0.7 high, >=0.4 medium.",
        "predictions": rows,
    }


def advise(db: Session, student: Student, course_code: str) -> dict:
    status = prereq_status(db, course_code, student_id=student.id)
    course = db.execute(select(Course).where(Course.code == course_code)).scalar_one_or_none()
    unmet = sorted(set(status["unmet"]))
    eligible = bool(status["exists"] and not unmet and not status["cycle"])
    if not status["exists"]:
        reason = f"Course {course_code} is not in the catalog."
    elif status["cycle"]:
        reason = f"{course_code} has a cycle in its prerequisite graph; registration is blocked."
    elif unmet:
        reason = f"Missing prerequisites: {', '.join(unmet)}."
    else:
        reason = "Eligible - all prerequisites completed."
    return {
        "course_code": course_code,
        "course_title": course.title if course else "",
        "exists": status["exists"],
        "eligible": eligible,
        "reason": reason,
        "direct_prerequisites": status["direct"],
        "unmet_prerequisites": unmet,
        "chain": [c["code"] for c in status["chain"]],
        "passed_codes": sorted(_passed_codes(db, student.id)),
    }


def get_today(db: Session, student: Student) -> dict:
    score = get_success_score(db, student)
    alerts = get_alerts(db, student)
    predictions = get_predictions(db, student)

    plan: list[dict] = [
        {
            "severity": a["severity"],
            "kind": a["kind"],
            "course_code": a["course_code"],
            "action": f"{a['detail']} {a['recommendation']}",
        }
        for a in alerts
    ]
    weak = sorted(
        [p for p in predictions["predictions"] if p["grade"] == "" and p["failure_risk"] >= PASS_PROB_BANDS[0]],
        key=lambda p: -p["failure_risk"],
    )[:3]
    for p in weak:
        plan.append(
            {
                "severity": "medium",
                "kind": "study",
                "course_code": p["course_code"],
                "action": (
                    f"Study {p['course_code']} ({p['title']}) - predicted pass probability "
                    f"{p['pass_probability']:.0%} is below comfortable levels."
                ),
            }
        )
    if not plan:
        plan.append(
            {
                "severity": "low",
                "kind": "status",
                "course_code": None,
                "action": "All clear - no alerts. Keep up the good work.",
            }
        )

    return {
        "student_id": student.student_id,
        "date": date.today().isoformat(),
        "success_score": score["success_score"],
        "risk_level": score["risk_level"],
        "plan": plan,
    }
