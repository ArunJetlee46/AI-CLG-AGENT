import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Course, Lecturer, Student

logger = logging.getLogger(__name__)
settings = get_settings()

_INTENT_CYPHER: dict[str, str] = {
    "overloaded_lecturers": (
        "MATCH (l:Lecturer)-[:TEACHES]->(c:Course) "
        "RETURN l.name AS lecturer, count(c) AS course_count ORDER BY course_count DESC LIMIT 10"
    ),
    "repeated_failures": (
        "MATCH (s:Student)-[:ENROLLED]->(c:Course)-[:HAS_RESULT]->(r:Result) "
        "WHERE r.grade IN ['F','E'] WITH s, c, count(r) AS fails WHERE fails >= 2 "
        "RETURN s.student_id AS student, c.code AS course, fails"
    ),
    "room_utilization": (
        "MATCH (r:Room)-[:HOSTS]->(t:TimetableEntry) "
        "RETURN r.room_no AS room, count(t) AS bookings ORDER BY bookings DESC"
    ),
    "default": (
        "MATCH (n) RETURN labels(n) AS labels, count(n) AS total "
        "ORDER BY total DESC LIMIT 10"
    ),
}


class GraphService:
    """NL intent -> Cypher -> Neo4j. Degrades gracefully when Neo4j is down."""

    def __init__(self) -> None:
        self._driver = None

    def _connect(self) -> None:
        if self._driver is not None:
            return
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            self._driver.verify_connectivity()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Neo4j unavailable (%s); knowledge queries will degrade", exc)
            self._driver = None

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        self._connect()
        if self._driver is None:
            raise RuntimeError("Neo4j is not available")
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(r) for r in result]

    def resolve_intent(self, text: str) -> str:
        lowered = text.lower()
        if any(k in lowered for k in ("overload", "course load", "busy lecturer")):
            return "overloaded_lecturers"
        if any(k in lowered for k in ("repeat", "failed twice", "failing", "repeated")):
            return "repeated_failures"
        if any(k in lowered for k in ("utilization", "room usage", "underused", "bookings")):
            return "room_utilization"
        return "default"

    def answer(self, text: str) -> tuple[str, str, list[dict]]:
        intent = self.resolve_intent(text)
        cypher = _INTENT_CYPHER.get(intent, _INTENT_CYPHER["default"])
        try:
            rows = self.query(cypher)
        except RuntimeError as exc:
            return "knowledge-query-degraded", "Neo4j unavailable: " + str(exc), []
        return intent, cypher, rows


def sync_graph_from_db(db: Session) -> dict[str, int]:
    """Rebuild Neo4j nodes/edges from PostgreSQL (read model refresh)."""
    from app.core.audit import record_event

    stats: dict[str, int] = {"students": 0, "courses": 0, "lecturers": 0}
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            for s in db.execute(select(Student)).scalars():
                session.run("MERGE (s:Student {student_id:$sid, program:$p})", sid=s.student_id, p=s.program)
                stats["students"] += 1
            for c in db.execute(select(Course)).scalars():
                session.run("MERGE (c:Course {code:$code, title:$t})", code=c.code, t=c.title)
                stats["courses"] += 1
            for l in db.execute(select(Lecturer)).scalars():
                session.run("MERGE (l:Lecturer {staff_id:$sid, department:$d})", sid=l.staff_id, d=l.department)
                stats["lecturers"] += 1
        driver.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Neo4j sync skipped: %s", exc)
    record_event(db, actor="system", action="graph_sync", entity_type="Neo4j", payload=stats)
    return stats


_graph: GraphService | None = None


def get_graph_service() -> GraphService:
    global _graph
    if _graph is None:
        _graph = GraphService()
    return _graph
