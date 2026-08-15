"""Tests for the Placement flow + intelligence (analytical batch).

Covers the 11-stage flow: company -> JD -> JD analyzer -> eligibility ->
matching/ranking -> officer notify -> rounds -> selection -> analytics, plus
funnel/salary/skill-demand/departments/prediction analytics.
"""
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import (
    AttendanceRecord,
    AuditLog,
    Company,
    Course,
    Enrollment,
    JobDescription,
    PlacementNotification,
    PlacementSelection,
    Result,
    Student,
    User,
)
from app.services import placement_intelligence as pi


def _make_company(db) -> str:
    row = pi.create_company(db, name="TechCorp", sector="Software", location="Kigali",
                            contact_email="hr@techcorp.rw", contact_phone="+250700000000",
                            notes="", actor="officer1")
    return row["id"]


def _make_jd(db, company_id: str) -> str:
    text = ("Software Engineer Intern. Requires Python, Java, SQL, communication. "
            "GPA 2.5, 0 backlogs, 2026 batch. CTC 12-18 LPA. Location Kigali.")
    jd = pi.create_jd(db, company_id=company_id, title="Software Engineer Intern", raw_text=text,
                      min_gpa=None, max_backlogs=None, ctc_min=None, ctc_max=None, openings=None, actor="officer1")
    return jd["id"]


def _make_student(db, sid: str, gpa: float, program: str = "Computer Science") -> None:
    user = User(username=f"pstu_{sid}", password_hash=hash_password("student123"), role="student",
                email=f"{sid}@beru.edu")
    db.add(user)
    db.flush()
    student = Student(user_id=user.id, student_id=sid, year=4, program=program, gpa=gpa)
    db.add(student)
    db.flush()
    titles = ("Programming in Python", "Communication Skills") if program == "Computer Science" \
        else ("Data Structures", "Business English")
    for title in titles:
        course = db.execute(select(Course).where(Course.title == title)).scalar_one_or_none()
        if course is None:
            course = Course(code=f"C{abs(hash(title)) % 10000}", title=title, credits=3,
                            department="General", prerequisites=[])
            db.add(course)
            db.flush()
        enrollment = Enrollment(student_id=student.id, course_id=course.id, status="approved")
        db.add(enrollment)
        db.flush()
        db.add(Result(enrollment_id=enrollment.id, marks=min(100.0, gpa * 25), grade="A" if gpa >= 3.0 else "B"))
        for day in range(1, 11):
            db.add(AttendanceRecord(enrollment_id=enrollment.id, day=date(2026, 1, day),
                                    status="present" if day <= 9 else "absent"))
    db.commit()


def _make_students(db, n: int = 3) -> list[str]:
    ids = [f"PSTU{1000 + i}" for i in range(n)]
    for i, sid in enumerate(ids):
        _make_student(db, sid, gpa=3.2 + 0.1 * i)
    return ids


def test_jd_analyzer_deterministic():
    db = SessionLocal()
    try:
        parsed = pi.analyze_jd_text(db, "Software Engineer. Python, Java, SQL, communication. GPA 3.0, 0 backlogs. CTC 12-18 LPA.")
        assert parsed["role_type"] == "software"
        assert "python" in parsed["skills"] and "communication" in parsed["skills"]
        assert parsed["ctc_min"] == 12 and parsed["ctc_max"] == 18
        assert parsed["min_gpa"] == 3.0
        assert parsed["method"] == "deterministic"
    finally:
        db.close()


def test_company_and_jd_flow_with_audit():
    db = SessionLocal()
    try:
        cid = _make_company(db)
        row = pi._company_row(db, cid)
        assert row["name"] == "TechCorp" and row["drives"] == 0
        jd_id = _make_jd(db, cid)
        jd = db.execute(select(JobDescription).where(JobDescription.id == jd_id)).scalar_one()
        assert "python" in jd.skills
        audit = db.execute(select(AuditLog)).scalars().all()
        actions = [a.action for a in audit]
        assert "company_created" in actions and "jd_created" in actions
    finally:
        db.close()


def test_matching_gates_and_ranking():
    db = SessionLocal()
    try:
        _make_students(db, 3)
        jd = db.execute(select(JobDescription).where(JobDescription.title == "Software Engineer Intern")).scalar_one_or_none()
        if jd is None:
            cid = _make_company(db)
            _make_jd(db, cid)
            jd = db.execute(select(JobDescription).order_by(JobDescription.created_at.desc())).scalars().first()
        res = pi.match_for_jd(db, jd, limit=500)
        assert "candidates" in res and "eligible_count" in res
        scores = [c["match_score"] for c in res["candidates"]]
        assert scores == sorted(scores, reverse=True)
        for c in res["candidates"]:
            assert c["gates"]["gpa_ok"] is True and c["gates"]["backlogs_ok"] is True
            assert 0 <= c["match_score"] <= 100
    finally:
        db.close()


def test_drive_rounds_notify_selection_pipeline():
    db = SessionLocal()
    try:
        jd = db.execute(select(JobDescription).order_by(JobDescription.created_at.desc())).scalars().first()
        drive = pi.create_drive(db, title="TechCorp Drive", company_id=jd.company_id, jd_id=jd.id,
                                drive_date=date(2026, 9, 1), mode="online", location="Kigali", actor="officer1")
        drive_id = drive["id"]
        pi.add_round(db, drive_id=drive_id, name="Aptitude", round_order=1, round_date=date(2026, 9, 5), actor="officer1")
        pi.add_round(db, drive_id=drive_id, name="Technical", round_order=2, round_date=date(2026, 9, 10), actor="officer1")
        match = pi.match_for_jd(db, jd, limit=20)
        ids = [c["student_id"] for c in match["candidates"][:3]]
        assert ids, "cohort should produce candidates"
        res = pi.notify_students(db, drive_id=drive_id, student_ids=ids, actor="officer1")
        assert res["notified"] == len(ids)
        student = db.execute(select(Student).where(Student.student_id == ids[0])).scalar_one()
        pi.record_selection(db, drive_id=drive_id, student_id=ids[0], round_reached="final",
                            offered_ctc=15.0, offer_status="offered", actor="officer1")
        notifs = db.execute(select(PlacementNotification).where(PlacementNotification.drive_id == drive_id)).scalars().all()
        assert len(notifs) == len(ids)
        pipe = pi.get_pipeline(db, drive_id)
        assert pipe["rounds"] == ["Aptitude", "Technical"]
        assert pipe["funnel"][0]["stage"] == "Notified"
        assert pipe["funnel"][-1]["count"] == 1
        assert len(db.execute(select(PlacementSelection).where(PlacementSelection.drive_id == drive_id)).scalars().all()) == 1
    finally:
        db.close()


def test_flow_status_and_analytics():
    db = SessionLocal()
    try:
        fs = pi.get_flow_status(db)
        keys = [s["key"] for s in fs["stages"]]
        assert keys == ["company", "jd_upload", "jd_analyzer", "eligibility", "matching",
                        "ranking", "officer_review", "notify", "rounds", "selection", "analytics"]
        assert fs["total_students"] > 0

        funnel = pi.get_funnel(db)
        assert funnel["cohort"] > 0
        assert "offer_rate_pct" in funnel["conversion"]

        salary = pi.get_salary_analytics(db)
        assert salary["overall"]["count"] >= 0

        demand = pi.get_skill_demand(db)
        assert demand["total_jds"] >= 1

        dept = pi.get_department_comparison(db)
        assert any(p["students"] > 0 for p in dept["programs"])

        pred = pi.get_placement_prediction(db)
        assert pred["predicted_placement_rate"] is not None

        training = pi.get_training_plans(db, limit=20)
        assert isinstance(training, list)

        gaps = pi.get_gap_analysis(db)
        assert "students" in gaps and "required_skills" in gaps

        coding = pi.get_coding_analytics(db)
        aptitude = pi.get_aptitude_analytics(db)
        comm = pi.get_communication_analytics(db)
        assert coding["kind"] == "coding" and aptitude["kind"] == "aptitude" and comm["kind"] == "communication"

        report = pi.get_reports(db)
        assert report["funnel"]["cohort"] > 0

        notifs = pi.get_notifications(db)
        assert "unread" in notifs
    finally:
        db.close()
