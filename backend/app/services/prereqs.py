"""Prerequisite graph traversal backed by a recursive CTE.

The brief calls for a recursive SQL query for prerequisite traversal (Neo4j
only if that falls short). `courses.prerequisites` is a JSON array of course
codes; the recursive CTE below walks it transitively from a root course.

The traversal is per-path cycle-guarded and depth-bounded, so it always
terminates. Each emitted row carries a `cycle` flag set when the edge points at
a course already on the current path. SQLite JSON is consumed via `json_each`;
the only change for Postgres would be `jsonb_array_elements_text` in place of
`json_each`.
"""
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.entities import Course, Enrollment, Result

MAX_DEPTH = 12

_RECURSIVE_SQL = text(
    """
    WITH RECURSIVE chain(code, depth, path, cycle) AS (
        SELECT :root, 0, :root, 0
        UNION ALL
        SELECT je.value,
               chain.depth + 1,
               chain.path || '>' || je.value,
               CASE WHEN instr('>' || chain.path || '>', '>' || je.value || '>') > 0
                    THEN 1 ELSE 0 END
        FROM chain
        JOIN courses c ON c.code = chain.code
        CROSS JOIN json_each(c.prerequisites) AS je
        WHERE chain.depth < :max_depth
          AND chain.cycle = 0
    )
    SELECT code, depth, path, cycle FROM chain WHERE depth > 0 ORDER BY depth, code
    """
)


def _traverse(db: Session, code: str) -> list:
    return db.execute(_RECURSIVE_SQL, {"root": code, "max_depth": MAX_DEPTH}).all()


def _root_exists(db: Session, code: str) -> bool:
    return db.execute(select(Course.code).where(Course.code == code)).scalar_one_or_none() is not None


def prereq_chain(db: Session, code: str) -> list[dict]:
    """Transitive prerequisite closure of `code`, nearest first.

    Returns [{"code", "depth", "path"}] deduplicated by code (first, shallowest
    occurrence wins). Empty when the root course does not exist.
    """
    if not _root_exists(db, code):
        return []
    seen: dict[str, dict] = {}
    for row in _traverse(db, code):
        if row.cycle or row.code in seen:
            continue
        seen[row.code] = {"code": row.code, "depth": row.depth, "path": row.path}
    return list(seen.values())


def has_cycle(db: Session, code: str) -> bool:
    """True when the prerequisite graph reachable from `code` contains a cycle."""
    if not _root_exists(db, code):
        return False
    return any(row.cycle for row in _traverse(db, code))


def prereq_status(db: Session, code: str, *, student_id: str | None = None) -> dict:
    """Full picture for one course: existence, direct prereqs, transitive chain,
    cycle detection, catalog-missing prereqs, and (when a student is given)
    which chain entries the student has not yet completed."""
    if not _root_exists(db, code):
        return {"code": code, "exists": False, "direct": [], "chain": [], "missing": [], "unmet": [], "cycle": False}

    rows = _traverse(db, code)
    chain = prereq_chain(db, code)
    direct = sorted({r.code for r in rows if r.depth == 1 and not r.cycle})
    known = {c for (c,) in db.execute(select(Course.code)).all()}
    chain_codes = {c["code"] for c in chain}
    missing = sorted(chain_codes - known)

    unmet: list[str] = []
    if student_id is not None:
        passed = {
            code for (code,) in db.execute(
                select(Course.code)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .join(Result, Result.enrollment_id == Enrollment.id)
                .where(Enrollment.student_id == student_id, Result.grade != "F")
            ).all()
        }
        unmet = sorted(chain_codes - passed)

    root = db.execute(select(Course).where(Course.code == code)).scalar_one()
    return {
        "code": code,
        "exists": True,
        "direct": sorted(root.prerequisites or []),
        "chain": chain,
        "missing": missing,
        "unmet": unmet,
        "cycle": any(r.cycle for r in rows),
    }
