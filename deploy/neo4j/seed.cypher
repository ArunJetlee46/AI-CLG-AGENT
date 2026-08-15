// =====================================================================
// Beru Campus AI - Neo4j Knowledge Graph seed (Phase 4)
// Idempotent: safe to run repeatedly (MERGE + IF NOT EXISTS constraints).
// Apply: docker compose exec neo4j cypher-shell -u neo4j -p beru-neo4j -f /data/seed.cypher
// =====================================================================

// ---- 1. Schema constraints (uniqueness) -----------------------------
CREATE CONSTRAINT student_id IF NOT EXISTS FOR (s:Student) REQUIRE s.student_id IS UNIQUE;
CREATE CONSTRAINT course_code IF NOT EXISTS FOR (c:Course) REQUIRE c.code IS UNIQUE;
CREATE CONSTRAINT lecturer_id IF NOT EXISTS FOR (l:Lecturer) REQUIRE l.staff_id IS UNIQUE;
CREATE CONSTRAINT room_no IF NOT EXISTS FOR (r:Room) REQUIRE r.room_no IS UNIQUE;
CREATE CONSTRAINT dept_name IF NOT EXISTS FOR (d:Department) REQUIRE d.name IS UNIQUE;

// ---- 2. Supporting indexes ------------------------------------------
CREATE INDEX IF NOT EXISTS FOR (s:Student) ON (s.program);
CREATE INDEX IF NOT EXISTS FOR (s:Student) ON (s.gpa);
CREATE INDEX IF NOT EXISTS FOR (l:Lecturer) ON (l.department);
CREATE INDEX IF NOT EXISTS FOR (l:Lecturer) ON (l.max_hours);
CREATE INDEX IF NOT EXISTS FOR (c:Course) ON (c.title);
CREATE INDEX IF NOT EXISTS FOR (c:Course) ON (c.department);

// ---- 3. Departments --------------------------------------------------
MERGE (d:Department {name: 'Computer Science'});
MERGE (d:Department {name: 'Engineering'});
MERGE (d:Department {name: 'Business'});

// ---- 4. Lecturers ----------------------------------------------------
MERGE (l:Lecturer {staff_id: 'LEC0000'}) ON CREATE SET l.name = 'Amina Okonkwo', l.department = 'Computer Science', l.max_hours = 24;
MERGE (l:Lecturer {staff_id: 'LEC0001'}) ON CREATE SET l.name = 'Kofi Mensah', l.department = 'Engineering', l.max_hours = 20;
MERGE (l:Lecturer {staff_id: 'LEC0002'}) ON CREATE SET l.name = 'Sade Akinola', l.department = 'Business', l.max_hours = 16;

// ---- 5. Courses + prerequisites --------------------------------------
MERGE (c:Course {code: 'CS101'}) ON CREATE SET c.title = 'Intro to Programming', c.credits = 3, c.capacity = 60, c.department = 'Computer Science';
MERGE (c:Course {code: 'CS202'}) ON CREATE SET c.title = 'Data Structures', c.credits = 3, c.capacity = 50, c.department = 'Computer Science';
MERGE (c:Course {code: 'CS302'}) ON CREATE SET c.title = 'Database Systems', c.credits = 4, c.capacity = 45, c.department = 'Computer Science';
MERGE (c:Course {code: 'ENG111'}) ON CREATE SET c.title = 'Engineering Math I', c.credits = 3, c.capacity = 80, c.department = 'Engineering';
MERGE (c:Course {code: 'BUS210'}) ON CREATE SET c.title = 'Quantitative Methods', c.credits = 3, c.capacity = 70, c.department = 'Business';

MATCH (a:Course {code: 'CS202'}), (b:Course {code: 'CS101'}) MERGE (a)-[:REQUIRES]->(b);
MATCH (a:Course {code: 'CS302'}), (b:Course {code: 'CS202'}) MERGE (a)-[:REQUIRES]->(b);
MATCH (a:Course {code: 'BUS210'}), (b:Course {code: 'ENG111'}) MERGE (a)-[:REQUIRES]->(b);

// ---- 6. Rooms --------------------------------------------------------
MERGE (r:Room {room_no: 'A001'}) ON CREATE SET r.capacity = 60, r.kind = 'lecture hall';
MERGE (r:Room {room_no: 'B102'}) ON CREATE SET r.capacity = 40, r.kind = 'lab';
MERGE (r:Room {room_no: 'C201'}) ON CREATE SET r.capacity = 80, r.kind = 'classroom';

// ---- 7. Students -----------------------------------------------------
MERGE (s:Student {student_id: 'STU00001'}) ON CREATE SET s.name = 'Zainab Bello', s.year = 2, s.program = 'Computer Science', s.gpa = 3.4;
MERGE (s:Student {student_id: 'STU00002'}) ON CREATE SET s.name = 'Chidi Osei', s.year = 2, s.program = 'Computer Science', s.gpa = 2.0;
MERGE (s:Student {student_id: 'STU00003'}) ON CREATE SET s.name = 'Lindiwe Dlamini', s.year = 3, s.program = 'Engineering', s.gpa = 2.6;
MERGE (s:Student {student_id: 'STU00004'}) ON CREATE SET s.name = 'Musa Balogun', s.year = 1, s.program = 'Business', s.gpa = 3.0;

// ---- 8. Affiliations / teaching -------------------------------------
MATCH (l:Lecturer {staff_id: 'LEC0000'}), (d:Department {name: 'Computer Science'}) MERGE (l)-[:WORKS_IN]->(d);
MATCH (l:Lecturer {staff_id: 'LEC0001'}), (d:Department {name: 'Engineering'}) MERGE (l)-[:WORKS_IN]->(d);
MATCH (l:Lecturer {staff_id: 'LEC0002'}), (d:Department {name: 'Business'}) MERGE (l)-[:WORKS_IN]->(d);

MATCH (s:Student {student_id: 'STU00001'}), (d:Department {name: 'Computer Science'}) MERGE (s)-[:STUDIES_IN]->(d);
MATCH (s:Student {student_id: 'STU00002'}), (d:Department {name: 'Computer Science'}) MERGE (s)-[:STUDIES_IN]->(d);
MATCH (s:Student {student_id: 'STU00003'}), (d:Department {name: 'Engineering'}) MERGE (s)-[:STUDIES_IN]->(d);
MATCH (s:Student {student_id: 'STU00004'}), (d:Department {name: 'Business'}) MERGE (s)-[:STUDIES_IN]->(d);

MATCH (c:Course {code: 'CS101'}), (l:Lecturer {staff_id: 'LEC0000'}) MERGE (l)-[:TEACHES]->(c);
MATCH (c:Course {code: 'CS202'}), (l:Lecturer {staff_id: 'LEC0000'}) MERGE (l)-[:TEACHES]->(c);
MATCH (c:Course {code: 'CS302'}), (l:Lecturer {staff_id: 'LEC0000'}) MERGE (l)-[:TEACHES]->(c);
MATCH (c:Course {code: 'ENG111'}), (l:Lecturer {staff_id: 'LEC0001'}) MERGE (l)-[:TEACHES]->(c);
MATCH (c:Course {code: 'BUS210'}), (l:Lecturer {staff_id: 'LEC0002'}) MERGE (l)-[:TEACHES]->(c);

MATCH (c:Course), (d:Department)
WHERE c.department = d.name
MERGE (c)-[:BELONGS_TO]->(d);

// ---- 9. Enrollments (with attendance_rate) ---------------------------
MATCH (s:Student {student_id: 'STU00001'}), (c:Course {code: 'CS101'})
MERGE (s)-[e:ENROLLED_IN {status: 'approved'}]->(c) SET e.attendance_rate = 0.92;
MATCH (s:Student {student_id: 'STU00001'}), (c:Course {code: 'CS202'})
MERGE (s)-[e:ENROLLED_IN {status: 'approved'}]->(c) SET e.attendance_rate = 0.85;
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS101'})
MERGE (s)-[e:ENROLLED_IN {status: 'approved'}]->(c) SET e.attendance_rate = 0.51;
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS202'})
MERGE (s)-[e:ENROLLED_IN {status: 'pending'}]->(c) SET e.attendance_rate = 0.0;
MATCH (s:Student {student_id: 'STU00003'}), (c:Course {code: 'ENG111'})
MERGE (s)-[e:ENROLLED_IN {status: 'approved'}]->(c) SET e.attendance_rate = 0.66;
MATCH (s:Student {student_id: 'STU00004'}), (c:Course {code: 'BUS210'})
MERGE (s)-[e:ENROLLED_IN {status: 'approved'}]->(c) SET e.attendance_rate = 0.88;

// ---- 10. Achieved results --------------------------------------------
MATCH (s:Student {student_id: 'STU00001'}), (c:Course {code: 'CS101'})
MERGE (s)-[a:ACHIEVED]->(c) SET a.grade = 'A', a.marks = 82.0, a.semester = '2025-S2';
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS101'})
MERGE (s)-[a:ACHIEVED]->(c) SET a.grade = 'F', a.marks = 31.0, a.semester = '2025-S2';
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS202'})
MERGE (s)-[a:ACHIEVED]->(c) SET a.grade = 'F', a.marks = 28.0, a.semester = '2025-S2';
MATCH (s:Student {student_id: 'STU00003'}), (c:Course {code: 'ENG111'})
MERGE (s)-[a:ACHIEVED]->(c) SET a.grade = 'C', a.marks = 55.0, a.semester = '2025-S2';

// ---- 11. Risk predictions --------------------------------------------
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS101'})
MERGE (s)-[p:PREDICTED_RISK]->(c) SET p.probability = 0.87, p.risk_level = 'high', p.model_version = 'xgb-v1', p.created_at = datetime();
MATCH (s:Student {student_id: 'STU00002'}), (c:Course {code: 'CS202'})
MERGE (s)-[p:PREDICTED_RISK]->(c) SET p.probability = 0.91, p.risk_level = 'high', p.model_version = 'xgb-v1', p.created_at = datetime();
MATCH (s:Student {student_id: 'STU00003'}), (c:Course {code: 'ENG111'})
MERGE (s)-[p:PREDICTED_RISK]->(c) SET p.probability = 0.58, p.risk_level = 'medium', p.model_version = 'xgb-v1', p.created_at = datetime();

// ---- 12. Scheduling ------------------------------------------------
MATCH (c:Course {code: 'CS101'}), (r:Room {room_no: 'A001'})
MERGE (c)-[sch:SCHEDULED_IN]->(r) SET sch.day = 'MON', sch.start_time = '08:00', sch.end_time = '10:00', sch.term = '2026-S1';
MATCH (c:Course {code: 'CS202'}), (r:Room {room_no: 'B102'})
MERGE (c)-[sch:SCHEDULED_IN]->(r) SET sch.day = 'TUE', sch.start_time = '10:00', sch.end_time = '12:00', sch.term = '2026-S1';
MATCH (c:Course {code: 'CS302'}), (r:Room {room_no: 'A001'})
MERGE (c)-[sch:SCHEDULED_IN]->(r) SET sch.day = 'THU', sch.start_time = '08:00', sch.end_time = '10:00', sch.term = '2026-S1';
MATCH (c:Course {code: 'ENG111'}), (r:Room {room_no: 'C201'})
MERGE (c)-[sch:SCHEDULED_IN]->(r) SET sch.day = 'WED', sch.start_time = '13:00', sch.end_time = '15:00', sch.term = '2026-S1';
MATCH (c:Course {code: 'BUS210'}), (r:Room {room_no: 'C201'})
MERGE (c)-[sch:SCHEDULED_IN]->(r) SET sch.day = 'FRI', sch.start_time = '10:00', sch.end_time = '12:00', sch.term = '2026-S1';

// ---- 13. Verification queries (expect rows / counts) -----------------
// Lecturers by course load:
//   MATCH (l:Lecturer)-[:TEACHES]->(c) RETURN l.staff_id, count(c) ORDER BY count(c) DESC;
// Students failing twice:
//   MATCH (s:Student)-[a:ACHIEVED]->(c) WHERE a.grade='F' WITH s,c,count(a) AS f WHERE f>=2 RETURN s.student_id,c.code,f;
// Room utilization:
//   MATCH (:Course)-[sch:SCHEDULED_IN]->(r:Room) RETURN r.room_no, count(sch) ORDER BY count(sch) DESC;
