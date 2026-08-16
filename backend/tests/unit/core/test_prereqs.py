"""Prerequisite traversal (Phase P5): recursive CTE + advising wiring."""
import pytest
from sqlalchemy import text

from app.agents.academic_ops import AcademicOpsAgent
from app.agents.supervisor import get_supervisor
from app.core.security import hash_password
from app.db import SessionLocal
from app.models.entities import Course, Enrollment, Result, Student, User
from app.services.prereqs import has_cycle, prereq_chain, prereq_status

CODES = {"PR101", "PR201", "PR301", "PRX1", "PRX2", "PRZZ"}


@pytest.fixture(scope="module")
def prereq_graph():
    db = SessionLocal()
    try:
        db.add_all(
            [
                Course(code="PR101", title="Intro", prerequisites=[]),
                Course(code="PR201", title="Intermediate", prerequisites=["PR101"]),
                Course(code="PR301", title="Advanced", prerequisites=["PR201"]),
                Course(code="PRX1", title="Cycle A", prerequisites=["PRX2"]),
                Course(code="PRX2", title="Cycle B", prerequisites=["PRX1"]),
                Course(code="PRZZ", title="Broken", prerequisites=["NOPE404"]),
            ]
        )
        db.commit()
    finally:
        db.close()

    s1, s2 = _mk_student("PRSTU1", passed=["PR201"]), _mk_student("PRSTU2", passed=["PR101", "PR201"])
    yield {"s1": s1, "s2": s2}

    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM decision_cards WHERE audit_log_id IN (SELECT id FROM audit_logs WHERE actor = 'prereq-tester')")
        )
        db.execute(text("DELETE FROM audit_logs WHERE actor = 'prereq-tester'"))
        for uid in (s1["user_id"], s2["user_id"]):
            db.execute(text("DELETE FROM approval_requests WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM students WHERE id = :s"), {"s": s1["id"] if uid == s1["user_id"] else s2["id"]})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        db.execute(text("DELETE FROM courses WHERE code IN (:c1, :c2, :c3, :c4, :c5, :c6)"),
                   {"c1": "PR101", "c2": "PR201", "c3": "PR301", "c4": "PRX1", "c5": "PRX2", "c6": "PRZZ"})
        db.commit()
    finally:
        db.close()


def _mk_student(sid: str, passed: list[str]) -> dict:
    db = SessionLocal()
    try:
        user = User(username=f"{sid.lower()}-u", password_hash=hash_password("Passw0rd!"), role="student", email="")
        db.add(user)
        db.flush()
        student = Student(user_id=user.id, student_id=sid, year=1, program="Computer Science", gpa=3.0)
        db.add(student)
        db.flush()
        for code in passed:
            course = db.execute(text("SELECT id FROM courses WHERE code = :c"), {"c": code}).scalar_one()
            enr = Enrollment(student_id=student.id, course_id=course, status="approved")
            db.add(enr)
            db.flush()
            db.add(Result(enrollment_id=enr.id, marks=80.0, grade="B", semester="2026-S1"))
        db.commit()
        return {"id": student.id, "user_id": user.id}
    finally:
        db.close()


def test_chain_is_transitive(prereq_graph) -> None:
    db = SessionLocal()
    try:
        chain = prereq_chain(db, "PR301")
        assert [c["code"] for c in chain] == ["PR201", "PR101"]
        assert chain[0]["depth"] == 1
        assert chain[1]["depth"] == 2
    finally:
        db.close()


def test_chain_empty_for_unknown_course(prereq_graph) -> None:
    db = SessionLocal()
    try:
        assert prereq_chain(db, "NOPE404") == []
        assert prereq_status(db, "NOPE404")["exists"] is False
    finally:
        db.close()


def test_cycle_detected_and_traversal_terminates(prereq_graph) -> None:
    db = SessionLocal()
    try:
        assert has_cycle(db, "PRX1") is True
        chain = prereq_chain(db, "PRX1")
        assert [c["code"] for c in chain] == ["PRX2"]
    finally:
        db.close()


def test_missing_catalog_prereq_flagged(prereq_graph) -> None:
    db = SessionLocal()
    try:
        status = prereq_status(db, "PRZZ")
        assert status["missing"] == ["NOPE404"]
    finally:
        db.close()


def test_unmet_prereqs_derived_from_student_results(prereq_graph) -> None:
    db = SessionLocal()
    try:
        s1 = prereq_graph["s1"]  # passed PR201 only
        status = prereq_status(db, "PR301", student_id=s1["id"])
        assert status["unmet"] == ["PR101"]
        assert status["missing"] == []

        s2 = prereq_graph["s2"]  # passed PR101 + PR201
        status = prereq_status(db, "PR301", student_id=s2["id"])
        assert status["unmet"] == []
    finally:
        db.close()


def test_advising_answers_prereq_question(prereq_graph) -> None:
    state = get_supervisor().invoke("what are the prerequisites for PR301", actor="prereq-tester")
    assert state["intent"] == "advising"  # dedicated advising agent (Theme A)
    assert state["agent"] == "advising"
    assert "directly requires: PR201" in state["answer"]
    assert "PR201 > PR101" in state["answer"]
    assert state["requires_approval"] is False


def test_register_blocked_by_transitive_unmet(prereq_graph) -> None:
    s1 = prereq_graph["s1"]
    state = get_supervisor().invoke("register me for PR301", actor="prereq-tester", actor_id=s1["user_id"])
    assert "blocked" in state["answer"].lower()
    assert "PR101" in state["answer"]
    assert state["requires_approval"] is False


def test_register_ok_when_all_prereqs_met(prereq_graph) -> None:
    s2 = prereq_graph["s2"]
    state = get_supervisor().invoke("register me for PR301", actor="prereq-tester", actor_id=s2["user_id"])
    assert state["requires_approval"] is True
    assert state["data"]["action"] == "register"
    assert state["data"]["course_codes"] == ["PR301"]
    assert state["data"]["validations"][0]["prereq_chain"] == ["PR201", "PR101"]


def test_agent_validate_directly_reports_transitive_reasons(prereq_graph) -> None:
    db = SessionLocal()
    try:
        agent = AcademicOpsAgent()
        s1 = prereq_graph["s1"]
        result = agent._validate(db, ["PR301"], student_id=s1["id"])
        assert result["ok"] is False
        assert any("PR101" in r for r in result["reasons"])
        assert result["checks"][0]["prereq_chain"] == ["PR201", "PR101"]
    finally:
        db.close()
