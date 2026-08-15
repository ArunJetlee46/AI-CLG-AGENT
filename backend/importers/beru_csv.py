"""Import the real campus dataset (beru data/ CSVs) into the application DB.

Replaces any existing rows (run with --reset to wipe first). Maps the bespoke
CSV column names onto the SQLAlchemy schema and normalizes values:

  * students.gpa         10-point CGPA -> 0-4 scale (divide by 2.5)
  * users.password_hash  fake DEMO hash -> real bcrypt (role demo password)
  * ctc_min / ctc_max    "7 LPA" -> 7.0 (float)
  * skills / prerequisites / shap_values / permissions  JSON strings -> lists/dicts
  * timetable_entries    lecturer assigned by course department, end = start+1h
  * predictions          course_id inferred from the student's first enrollment

Usage (from backend/):
    .venv/Scripts/python.exe -m importers.beru_csv [--reset]
"""
import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.models import entities

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "beru data"

ROLE_PASSWORD = {
    "student": "student123",
    "lecturer": "lecturer123",
    "placement": "placement123",
    "admin": "admin123",
}


def _rows(name: str) -> list[dict]:
    path = DATA_DIR / f"{name}.csv"
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _json(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _parse_ctc(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(str(value).strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


def _gpa_10_to_4(value: str) -> float:
    try:
        return round(float(value) / 2.5, 2)
    except (TypeError, ValueError):
        return 0.0


def _time_plus_hour(start: str) -> datetime:
    parsed = datetime.strptime(start, "%H:%M")
    return parsed + timedelta(hours=1)


def wipe(db) -> None:
    for table in reversed(entities.Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def import_all(db) -> dict[str, int]:
    stats: dict[str, int] = {}

    # ---- users (identity) -------------------------------------------------
    user_id_map: dict[str, str] = {}
    for row in _rows("users"):
        username = row["username"]
        role = row["role"]
        user = entities.User(
            username=username,
            password_hash=hash_password(ROLE_PASSWORD.get(role, "admin123")),
            role=role,
            email=row.get("email", ""),
            is_active=(row.get("is_active", "1") == "1"),
        )
        db.add(user)
        db.flush()
        user_id_map[row["id"]] = user.id
    db.commit()
    stats["users"] = len(user_id_map)

    # ---- students / lecturers / admins ------------------------------------
    student_by_csv_user: dict[str, entities.Student] = {}
    for row in _rows("students"):
        student = entities.Student(
            user_id=user_id_map[row["user_id"]],
            student_id=row["student_id"],
            year=int(row.get("year", 1)),
            program=row.get("program", ""),
            gpa=_gpa_10_to_4(row.get("gpa", "0")),
        )
        db.add(student)
        db.flush()
        student_by_csv_user[row["user_id"]] = student
    db.commit()
    stats["students"] = len(_rows("students"))

    for row in _rows("lecturers"):
        db.add(
            entities.Lecturer(
                user_id=user_id_map[row["user_id"]],
                staff_id=row["staff_id"],
                department=row.get("department", ""),
                max_hours=int(row.get("max_hours", 20)),
            )
        )
    db.commit()
    stats["lecturers"] = len(_rows("lecturers"))

    for row in _rows("admins"):
        db.add(
            entities.Admin(
                user_id=user_id_map[row["user_id"]],
                permissions=_json(row.get("permissions", "[]")) or [],
            )
        )
    db.commit()
    stats["admins"] = len(_rows("admins"))

    # ---- courses / rooms --------------------------------------------------
    course_id_map: dict[str, str] = {}  # csv id -> db id
    for row in _rows("courses"):
        course = entities.Course(
            code=row["code"],
            title=row["title"],
            credits=int(row.get("credits", 3)),
            capacity=int(row.get("capacity", 60)),
            department=row.get("department", ""),
            prerequisites=_json(row.get("prerequisites", "[]")) or [],
        )
        db.add(course)
        db.flush()
        course_id_map[row["id"]] = course.id
    db.commit()
    stats["courses"] = len(course_id_map)

    room_id_map: dict[str, str] = {}  # csv id -> db id
    for row in _rows("rooms"):
        room = entities.Room(
            room_no=row["name"],
            capacity=int(row.get("capacity", 50)),
            kind="classroom",
        )
        db.add(room)
        db.flush()
        room_id_map[row["id"]] = room.id
    db.commit()
    stats["rooms"] = len(room_id_map)

    # ---- placement: companies / jobs / drives / rounds --------------------
    company_id_map: dict[str, str] = {}
    for row in _rows("companies"):
        company = entities.Company(
            name=row["name"],
            sector=row.get("industry", ""),
        )
        db.add(company)
        db.flush()
        company_id_map[row["id"]] = company.id
    db.commit()
    stats["companies"] = len(company_id_map)

    jd_id_map: dict[str, str] = {}
    for row in _rows("job_descriptions"):
        jd = entities.JobDescription(
            company_id=company_id_map[row["company_id"]],
            title=row["title"],
            skills=_json(row.get("skills", "[]")) or [],
            min_gpa=float(row.get("min_gpa", 2.5) or 2.5),
            max_backlogs=int(row.get("max_backlogs", 0) or 0),
            ctc_min=_parse_ctc(row.get("ctc_min")),
            ctc_max=_parse_ctc(row.get("ctc_max")),
            status="open",
        )
        db.add(jd)
        db.flush()
        jd_id_map[row["id"]] = jd.id
    db.commit()
    stats["job_descriptions"] = len(jd_id_map)

    drive_id_map: dict[str, str] = {}
    for row in _rows("placement_drives"):
        drive = entities.PlacementDrive(
            title=row["title"],
            company_id=company_id_map[row["company_id"]],
            jd_id=None,
            drive_date=datetime.strptime(row["start_date"], "%Y-%m-%d").date(),
            mode="online",
            status=row.get("status", "scheduled"),
        )
        db.add(drive)
        db.flush()
        drive_id_map[row["id"]] = drive.id
    db.commit()
    stats["placement_drives"] = len(drive_id_map)

    for row in _rows("recruitment_rounds"):
        db.add(
            entities.RecruitmentRound(
                drive_id=drive_id_map[row["drive_id"]],
                name=row.get("round_type", ""),
                round_order=int(row.get("round_no", 1)),
                round_date=db.get(entities.PlacementDrive, drive_id_map[row["drive_id"]]).drive_date,
                status=row.get("status", "scheduled"),
            )
        )
    db.commit()
    stats["recruitment_rounds"] = len(_rows("recruitment_rounds"))

    # ---- enrollments / results / attendance -------------------------------
    course_by_code: dict[str, entities.Course] = {c.code: c for c in db.query(entities.Course).all()}
    enrollment_id_map: dict[str, str] = {}  # csv id -> db id

    for row in _rows("enrollments"):
        student = student_by_csv_user.get(row["student_user_id"])
        course = course_by_code.get(row["course_code"])
        if student is None or course is None:
            continue
        enr = entities.Enrollment(
            student_id=student.id,
            course_id=course.id,
            status=row.get("status", "approved"),
            approval_id=None,
        )
        db.add(enr)
        db.flush()
        enrollment_id_map[row["id"]] = enr.id
    db.commit()
    stats["enrollments"] = len(enrollment_id_map)

    for row in _rows("results"):
        enr_id = enrollment_id_map.get(row["enrollment_id"])
        if enr_id is None:
            continue
        db.add(
            entities.Result(
                enrollment_id=enr_id,
                marks=float(row.get("marks", 0) or 0),
                grade=row.get("grade", ""),
                semester=row.get("semester", ""),
            )
        )
    db.commit()
    stats["results"] = len(_rows("results"))

    for row in _rows("attendance"):
        enr_id = enrollment_id_map.get(row["enrollment_id"])
        if enr_id is None:
            continue
        db.add(
            entities.AttendanceRecord(
                enrollment_id=enr_id,
                day=datetime.strptime(row["day"], "%Y-%m-%d").date(),
                status=row.get("status", "present"),
            )
        )
    db.commit()
    stats["attendance"] = len(_rows("attendance"))

    # ---- timetable (assign lecturer by course department) -----------------
    lecturer_by_dept: dict[str, list[entities.Lecturer]] = {}
    all_lecturers: list[entities.Lecturer] = []
    for l in db.query(entities.Lecturer).all():
        all_lecturers.append(l)
        lecturer_by_dept.setdefault(l.department, []).append(l)

    room_by_no: dict[str, entities.Room] = {r.room_no: r for r in db.query(entities.Room).all()}

    def pick_lecturer(course: entities.Course) -> entities.Lecturer:
        dept = course.department
        if dept in lecturer_by_dept:
            return lecturer_by_dept[dept][0]
        if all_lecturers:
            return all_lecturers[0]
        raise RuntimeError("No lecturers in DB; cannot build timetable")

    for row in _rows("timetable_entries"):
        course = course_by_code.get(row["course_code"])
        room = room_by_no.get(row["room"])
        if course is None or room is None:
            continue
        db.add(
            entities.TimetableEntry(
                course_id=course.id,
                room_id=room.id,
                lecturer_id=pick_lecturer(course).id,
                day=row.get("day", ""),
                start_time=datetime.strptime(row["start_time"], "%H:%M").time(),
                end_time=_time_plus_hour(row["start_time"]).time(),
                term="2026-S1",
            )
        )
    db.commit()
    stats["timetable_entries"] = len(_rows("timetable_entries"))

    # ---- placement selections / notifications -----------------------------
    for row in _rows("placement_selections"):
        student = student_by_csv_user.get(row["student_user_id"])
        drive = drive_id_map.get(row["drive_id"])
        if student is None or drive is None:
            continue
        db.add(
            entities.PlacementSelection(
                drive_id=drive,
                student_id=student.id,
                offered_ctc=float(row.get("offered_ctc", 0) or 0),
                offer_status=row.get("offer_status", "offered"),
            )
        )
    db.commit()
    stats["placement_selections"] = len(_rows("placement_selections"))

    for row in _rows("placement_notifications"):
        drive_id = drive_id_map.get(row["id"])
        for student in student_by_csv_user.values():
            db.add(
                entities.PlacementNotification(
                    drive_id=drive_id,
                    student_id=student.id,
                    title=row.get("title", ""),
                    body=row.get("message", ""),
                    status="sent" if row.get("is_active", "1") == "1" else "inactive",
                    created_at=datetime.strptime(row["publish_date"], "%Y-%m-%d"),
                )
            )
    db.commit()
    stats["placement_notifications"] = len(_rows("placement_notifications")) * len(student_by_csv_user)

    # ---- ML: predictions + intervention plans -----------------------------
    first_course: dict[str, str] = {}
    for enr in db.query(entities.Enrollment).all():
        first_course.setdefault(enr.student_id, enr.course_id)

    for row in _rows("predictions"):
        student = student_by_csv_user.get(row["student_user_id"])
        if student is None:
            continue
        db.add(
            entities.Prediction(
                student_id=student.id,
                course_id=first_course.get(student.id),
                probability=float(row.get("probability", 0) or 0),
                risk_level=row.get("risk_level", "medium"),
                shap_values=_json(row.get("shap_values", "{}")) or {},
                model_version=row.get("model_version", ""),
            )
        )
    db.commit()
    stats["predictions"] = len(_rows("predictions"))

    for row in _rows("intervention_plans"):
        student = student_by_csv_user.get(row["student_user_id"])
        if student is None:
            continue
        db.add(
            entities.InterventionPlan(
                student_id=student.id,
                plan_text=row.get("recommendation", ""),
                status=row.get("status", "drafted"),
            )
        )
    db.commit()
    stats["intervention_plans"] = len(_rows("intervention_plans"))

    # ---- governance: approvals / audit / decision cards / models ----------
    admin_ids = [a.user_id for a in db.query(entities.Admin).all()] or [next(iter(user_id_map.values()))]
    for row in _rows("approval_requests"):
        db.add(
            entities.ApprovalRequest(
                user_id=admin_ids[0],
                intent=row.get("entity_type", ""),
                payload={
                    "entity_id": row.get("entity_id", ""),
                    "requested_by": row.get("requested_by", ""),
                    "description": row.get("description", ""),
                },
                status=row.get("status", "pending"),
            )
        )
    db.commit()
    stats["approval_requests"] = len(_rows("approval_requests"))

    audit_log_id_map: dict[str, str] = {}
    for row in _rows("audit_logs"):
        entry = entities.AuditLog(
            actor=row.get("actor", ""),
            action=row.get("action", ""),
            entity_type="seed_import",
            entity_id=row.get("id"),
            payload=row.get("payload", ""),
            prev_hash=row.get("previous_hash", "GENESIS"),
            hash=row.get("hash", ""),
        )
        db.add(entry)
        db.flush()
        audit_log_id_map[row["id"]] = entry.id
    db.commit()
    stats["audit_logs"] = len(audit_log_id_map)

    first_audit_id = next(iter(audit_log_id_map.values())) if audit_log_id_map else None
    for row in _rows("decision_cards"):
        if first_audit_id is None:
            break
        db.add(
            entities.DecisionCard(
                audit_log_id=first_audit_id,
                decision_type=row.get("title", ""),
                inputs={},
                reasoning=row.get("description", ""),
                model_version="",
            )
        )
    db.commit()
    stats["decision_cards"] = len(_rows("decision_cards"))

    for row in _rows("models"):
        try:
            trained_at = datetime.strptime(row["trained_on"], "%Y-%m-%d")
        except (KeyError, ValueError):
            trained_at = datetime.utcnow()
        db.add(
            entities.ModelRecord(
                name=row.get("name", ""),
                version=row.get("version", "1.0"),
                metrics={"algorithm": row.get("algorithm", ""), "status": row.get("status", "")},
                is_active=(row.get("status") == "active"),
                trained_at=trained_at,
            )
        )
    db.commit()
    stats["models"] = len(_rows("models"))

    # ---- admin extras -----------------------------------------------------
    for row in _rows("announcements"):
        db.add(
            entities.Announcement(
                title=row.get("title", ""),
                body=row.get("message", ""),
                audience=row.get("audience", "all"),
                created_at=datetime.strptime(row["publish_date"], "%Y-%m-%d"),
            )
        )
    db.commit()
    stats["announcements"] = len(_rows("announcements"))

    for row in _rows("campus_resources"):
        db.add(
            entities.CampusResource(
                name=row.get("name", ""),
                resource_type=row.get("type", "classroom"),
                capacity=int(row.get("capacity", 0) or 0),
                location=row.get("building", ""),
                status=row.get("status", "active"),
            )
        )
    db.commit()
    stats["campus_resources"] = len(_rows("campus_resources"))

    for row in _rows("backups"):
        db.add(
            entities.BackupRecord(
                filename=row.get("path", ""),
                kind=row.get("database_type", "manual"),
                status=row.get("status", "completed"),
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "")) if "created_at" in row else datetime.utcnow(),
            )
        )
    db.commit()
    stats["backups"] = len(_rows("backups"))

    for row in _rows("research_projects"):
        db.add(
            entities.ResearchProject(
                title=row.get("title", ""),
                department=row.get("department", ""),
                status=row.get("status", "active"),
                start_year=int(row.get("year", 2025) or 2025),
            )
        )
    db.commit()
    stats["research_projects"] = len(_rows("research_projects"))

    for row in _rows("industry_partners"):
        db.add(
            entities.IndustryPartner(
                name=row.get("name", ""),
                sector=row.get("industry", ""),
                active=True,
            )
        )
    db.commit()
    stats["industry_partners"] = len(_rows("industry_partners"))

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import beru data CSVs into the app DB")
    parser.add_argument("--reset", action="store_true", help="wipe all existing rows before importing")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.reset:
            wipe(db)
            print("Database wiped")
        stats = import_all(db)
        print("Imported beru data:")
        for name, count in stats.items():
            print(f"  {name}: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
