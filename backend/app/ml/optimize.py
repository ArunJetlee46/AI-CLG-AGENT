"""Timetable optimization - constraint satisfaction via Google OR-Tools CP-SAT.

Hard constraints (must hold):
  H1  every course scheduled exactly once per week
  H2  room unary capacity - at most one course per (room, day, slot)
  H3  room capacity - room.size >= course.capacity (no oversubscribed room)
  H4  lab constraint - lab-needed courses only in lab rooms
  H5  faculty constraint - a lecturer never teaches two courses in the same slot
      (and never more than 2 sessions on the same day is a soft objective)

Soft constraints (objective to minimize):
  S1  room fit - avoid wasting a much larger room than needed
  S2  lab room used by a non-lab course (allowed but penalized)
  S3  lecturer daily spread - distribute sessions across the week

When OR-Tools is not installed (requirements-ml.txt), a deterministic greedy
heuristic produces the same report shape with status='heuristic'.
"""
import logging
from dataclasses import dataclass, field
from datetime import time

from sqlalchemy import select

from app.models.entities import Course, Lecturer, Room, TimetableEntry

logger = logging.getLogger(__name__)

DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
SLOTS = [("08:00", "10:00"), ("10:00", "12:00"), ("13:00", "15:00"), ("15:00", "17:00")]


def _needs_lab(title: str) -> bool:
    return "lab" in title.lower()


# ---------------------------------------------------------------------------
# Input shaping
# ---------------------------------------------------------------------------


@dataclass
class TimetableInput:
    courses: list[dict] = field(default_factory=list)
    rooms: list[dict] = field(default_factory=list)
    lecturer_of: dict[str, str] = field(default_factory=dict)  # course_id -> lecturer_id
    existing_entries: int = 0


def build_input(db) -> TimetableInput:
    courses = db.execute(select(Course)).scalars().all()
    rooms = db.execute(select(Room)).scalars().all()
    lecturers = db.execute(select(Lecturer)).scalars().all()

    lecturer_of: dict[str, str] = {}
    for entry in db.execute(select(TimetableEntry)).scalars():
        lecturer_of.setdefault(entry.course_id, entry.lecturer_id)
    fallback = [l.id for l in sorted(lecturers, key=lambda l: l.staff_id)]
    idx = 0
    for course in sorted(courses, key=lambda c: c.code):
        if course.id not in lecturer_of:
            if fallback:
                lecturer_of[course.id] = fallback[idx % len(fallback)]
                idx += 1

    return TimetableInput(
        courses=[
            {
                "id": c.id,
                "code": c.code,
                "title": c.title,
                "capacity": max(1, c.capacity or 50),
                "needs_lab": _needs_lab(c.title),
            }
            for c in courses
        ],
        rooms=[
            {
                "id": r.id,
                "room_no": r.room_no,
                "capacity": max(1, r.capacity or 50),
                "is_lab": r.kind == "lab",
            }
            for r in rooms
        ],
        lecturer_of=lecturer_of,
        existing_entries=len(db.execute(select(TimetableEntry)).scalars().all()),
    )


def _room_fit_penalty(room: dict, course: dict) -> int:
    """S1: heavy waste penalty when the room is more than 2x too large."""
    if room["capacity"] >= course["capacity"]:
        return 1 if room["capacity"] > 2 * course["capacity"] else 0
    return 1000  # infeasible fit (should be caught by H3)


def _assignment_score(room: dict, course: dict) -> int:
    score = 0
    if room["is_lab"] and not course["needs_lab"]:
        score += 3  # S2
    score += _room_fit_penalty(room, course)
    return score


# ---------------------------------------------------------------------------
# OR-Tools CP-SAT solver
# ---------------------------------------------------------------------------


def _solve_cpsat(inp: TimetableInput, time_limit: float = 10.0, relaxed: bool = False) -> dict:
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    n_slots = len(DAYS) * len(SLOTS)

    X: dict[tuple[int, int, int, int], object] = {}
    for ci, course in enumerate(inp.courses):
        for ri, room in enumerate(inp.rooms):
            if room["capacity"] < course["capacity"]:  # H3: room too small
                continue
            if course["needs_lab"] and not room["is_lab"]:  # H4: lab course in lab room
                continue
            for di in range(len(DAYS)):
                for si in range(len(SLOTS)):
                    X[(ci, ri, di, si)] = model.NewBoolVar(
                        f"X_{course['code']}_{room['room_no']}_{DAYS[di]}_{SLOTS[si][0]}"
                    )

    for ci, course in enumerate(inp.courses):
        scope = [var for (c, _, _, _), var in X.items() if c == ci]
        if scope:
            if relaxed:
                model.Add(sum(scope) <= 1)  # allow unscheduled when relaxing
            else:
                model.AddExactlyOne(scope)  # H1
        elif not relaxed:
            return {"status": "infeasible", "reason": f"no room fits {course['code']}"}

    for ri in range(len(inp.rooms)):
        for di in range(len(DAYS)):
            for si in range(len(SLOTS)):
                scope = [var for (_, r, d, s), var in X.items() if r == ri and d == di and s == si]
                if len(scope) > 1:
                    model.Add(sum(scope) <= 1)  # H2 room unary

    lecturers = sorted({lid for lid in inp.lecturer_of.values() if lid})
    by_lecturer: dict[str, list[int]] = {lid: [] for lid in lecturers}
    for ci, course in enumerate(inp.courses):
        lid = inp.lecturer_of.get(course["id"])
        if lid in by_lecturer:
            by_lecturer[lid].append(ci)

    for lid, courses_of in by_lecturer.items():
        if not courses_of:
            continue
        for di in range(len(DAYS)):
            for si in range(len(SLOTS)):
                scope = [
                    var for (c, _, d, s), var in X.items()
                    if c in courses_of and d == di and s == si
                ]
                if len(scope) > 1:
                    model.Add(sum(scope) <= 1)  # H5 faculty unary

    over: list[object] = []
    for lid, courses_of in by_lecturer.items():
        if not courses_of:
            continue
        for di in range(len(DAYS)):
            day_vars = [
                var for (c, _, d, _), var in X.items()
                if c in courses_of and d == di
            ]
            if len(day_vars) > 2:
                exceeds = model.NewIntVar(0, len(day_vars), f"over_{lid}_{di}")
                model.Add(sum(day_vars) <= 2 + exceeds)  # S3 daily spread
                over.append(exceeds)

    soft_terms = []
    for (ci, ri, di, si), var in X.items():
        soft_terms.append(var * _assignment_score(inp.rooms[ri], inp.courses[ci]))
    objective = sum(soft_terms) + sum(over)
    model.Minimize(objective)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 4
    solver.parameters.log_search_progress = False
    status_code = solver.Solve(model)

    status = solver.StatusName(status_code)
    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": status, "reason": "no solution found"}

    scheduled: list[dict] = []
    for (ci, ri, di, si), var in X.items():
        if solver.Value(var) == 1:
            scheduled.append(
                {
                    "course_id": inp.courses[ci]["id"],
                    "course_code": inp.courses[ci]["code"],
                    "room_id": inp.rooms[ri]["id"],
                    "room_no": inp.rooms[ri]["room_no"],
                    "lecturer_id": inp.lecturer_of.get(inp.courses[ci]["id"]),
                    "day": DAYS[di],
                    "start": SLOTS[si][0],
                    "end": SLOTS[si][1],
                }
            )
    return {"status": status, "scheduled": scheduled,
            "unscheduled": [c["id"] for c in inp.courses if c["id"] not in {s["course_id"] for s in scheduled}]}


# ---------------------------------------------------------------------------
# Greedy heuristic fallback (deterministic, no dependencies)
# ---------------------------------------------------------------------------


def _solve_heuristic(inp: TimetableInput) -> dict:
    courses = sorted(inp.courses, key=lambda c: (0 if c["needs_lab"] else 1, -c["capacity"], c["code"]))
    rooms = sorted(inp.rooms, key=lambda r: (r["room_no"], r["capacity"]))
    used: set[tuple[str, str, int, int]] = set()  # (room_id, day, slot)
    lecturer_slots: dict[str, set[tuple[int, int]]] = {}
    scheduled: list[dict] = []
    unscheduled: list[str] = []

    for course in courses:
        best: dict | None = None
        for room in rooms:
            if room["capacity"] < course["capacity"]:
                continue
            if course["needs_lab"] and not room["is_lab"]:
                continue
            for di, day in enumerate(DAYS):
                for si in range(len(SLOTS)):
                    if (room["id"], day, si) in used:
                        continue
                    lid = inp.lecturer_of.get(course["id"])
                    if lid and (di, si) in lecturer_slots.get(lid, set()):
                        continue
                    score = _assignment_score(room, course) + _daily_spread_penalty(lid, di, lecturer_slots)
                    candidate = {"score": score, "entry": {
                        "course_id": course["id"], "course_code": course["code"],
                        "room_id": room["id"], "room_no": room["room_no"],
                        "lecturer_id": lid, "day": day,
                        "start": SLOTS[si][0], "end": SLOTS[si][1],
                    }, "key": (room["id"], day, si)}
                    if best is None or score < best["score"]:
                        best = candidate
        if best is None:
            unscheduled.append(course["id"])
            continue
        used.add(best["key"])
        lid = best["entry"]["lecturer_id"]
        day_idx = DAYS.index(best["entry"]["day"])
        slot_idx = SLOTS.index((best["entry"]["start"], best["entry"]["end"]))
        lecturer_slots.setdefault(lid, set()).add((day_idx, slot_idx))
        scheduled.append(best["entry"])

    conflicts = len(unscheduled)
    status = "heuristic"
    return {"status": status, "scheduled": scheduled, "unscheduled": unscheduled,
            "conflicts": conflicts}


def _daily_spread_penalty(lid: str | None, day_idx: int, lecturer_slots: dict) -> int:
    if lid is None:
        return 0
    same_day = sum(1 for (d, _) in lecturer_slots.get(lid, set()) if d == day_idx)
    return max(0, same_day - 1) * 2  # S3


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def solve_timetable(db, *, approval_id: str | None = None, term: str = "2026-S1", time_limit: float = 10.0) -> dict:
    """Build a conflict-free weekly timetable.

    Returns a report with keys kept for back-compat with the ResourceOptimizer
    agent: courses, rooms, slots, existing_entries, conflicts, status (+ extras).

    The write path is approval-gated: rows are only persisted when an
    `approval_id` for an approved request is supplied (enforced inside this
    method). Without one, the solve is strictly propose-only.
    """
    inp = build_input(db)
    slots = len(DAYS) * len(SLOTS)
    result: dict | None = None
    algorithm = "heuristic"

    try:
        from ortools.sat.python import cp_model  # noqa: F401

        result = _solve_cpsat(inp, time_limit=time_limit)
        if result.get("status") in ("OPTIMAL", "FEASIBLE"):
            algorithm = "cp-sat"
        elif result.get("status") == "INFEASIBLE":
            relaxed = _solve_cpsat(inp, time_limit=time_limit, relaxed=True)
            if relaxed.get("status") in ("OPTIMAL", "FEASIBLE"):
                algorithm, result = "cp-sat-relaxed", relaxed
            else:
                logger.warning("CP-SAT infeasible (%s); falling back to greedy", result.get("reason"))
                result = _solve_heuristic(inp)
        else:
            logger.warning("CP-SAT %s; falling back to greedy", result.get("status"))
            result = _solve_heuristic(inp)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OR-Tools unavailable (%s); using greedy heuristic", exc)
        result = _solve_heuristic(inp)

    scheduled = result.get("scheduled", [])
    unscheduled = result.get("unscheduled", [])
    if scheduled and approval_id:
        from app.core.approvals import require_approved

        require_approved(db, approval_id)
        existing = db.execute(select(TimetableEntry)).scalars().all()
        for entry in existing:
            db.delete(entry)
        for s in scheduled:
            db.add(
                TimetableEntry(
                    course_id=s["course_id"],
                    room_id=s["room_id"],
                    lecturer_id=s["lecturer_id"],
                    day=s["day"],
                    start_time=time(int(s["start"][:2]), int(s["start"][3:5])),
                    end_time=time(int(s["end"][:2]), int(s["end"][3:5])),
                    term=term,
                )
            )
        db.commit()

    return {
        "courses": len(inp.courses),
        "rooms": len(inp.rooms),
        "slots": slots,
        "existing_entries": inp.existing_entries,
        "scheduled": len(scheduled),
        "unscheduled": unscheduled,
        "conflicts": len(unscheduled),
        "algorithm": algorithm,
        "status": result.get("status", "unknown"),
        "warnings": [result["reason"]] if result.get("reason") else [],
        "entries": scheduled,
    }
