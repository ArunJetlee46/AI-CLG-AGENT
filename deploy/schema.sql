-- =====================================================================
-- Beru Campus AI - PostgreSQL Schema (Phase 3)
-- Source of truth for the multi-agent university operating system.
-- Mirrors backend/app/models/entities.py (SQLAlchemy).
-- =====================================================================

BEGIN;

SET search_path TO public;

-- ---------------------------------------------------------------------
-- 1. users (+ role profiles)
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id            VARCHAR(36) PRIMARY KEY,
    username      VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(16) NOT NULL,
    email         VARCHAR(128) NOT NULL DEFAULT '',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_role CHECK (role IN ('student', 'lecturer', 'admin'))
);

CREATE UNIQUE INDEX uq_users_username ON users (username);
CREATE INDEX ix_users_role ON users (role);

CREATE TABLE students (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    student_id VARCHAR(16) NOT NULL,
    year       INT NOT NULL DEFAULT 1,
    program    VARCHAR(128) NOT NULL DEFAULT '',
    gpa        DOUBLE PRECISION NOT NULL DEFAULT 0.0
);
CREATE UNIQUE INDEX uq_students_student_id ON students (student_id);
ALTER TABLE students ADD CONSTRAINT chk_students_year CHECK (year BETWEEN 1 AND 10);
ALTER TABLE students ADD CONSTRAINT chk_students_gpa CHECK (gpa >= 0.0 AND gpa <= 4.0);

CREATE TABLE lecturers (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    staff_id   VARCHAR(16) NOT NULL,
    department VARCHAR(128) NOT NULL DEFAULT '',
    max_hours  INT NOT NULL DEFAULT 20
);
CREATE UNIQUE INDEX uq_lecturers_staff_id ON lecturers (staff_id);

CREATE TABLE admins (
    id          VARCHAR(36) PRIMARY KEY,
    user_id     VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- ---------------------------------------------------------------------
-- 2. Academic catalogue
-- ---------------------------------------------------------------------
CREATE TABLE courses (
    id            VARCHAR(36) PRIMARY KEY,
    code          VARCHAR(16) NOT NULL,
    title         VARCHAR(128) NOT NULL,
    credits       INT NOT NULL DEFAULT 3,
    capacity      INT NOT NULL DEFAULT 60,
    department    VARCHAR(128) NOT NULL DEFAULT '',
    prerequisites JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE UNIQUE INDEX uq_courses_code ON courses (code);
ALTER TABLE courses ADD CONSTRAINT chk_courses_credits CHECK (credits BETWEEN 1 AND 6);
ALTER TABLE courses ADD CONSTRAINT chk_courses_capacity CHECK (capacity >= 0);

-- ---------------------------------------------------------------------
-- 3. Enrollments, results, attendance
-- ---------------------------------------------------------------------
CREATE TABLE enrollments (
    id          VARCHAR(36) PRIMARY KEY,
    student_id  VARCHAR(36) NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id   VARCHAR(36) NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    status      VARCHAR(16) NOT NULL DEFAULT 'pending',
    enrolled_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT chk_enrollments_status CHECK (status IN ('pending', 'approved', 'rejected'))
);
CREATE UNIQUE INDEX uq_enrollment_student_course ON enrollments (student_id, course_id);
CREATE INDEX ix_enrollments_student ON enrollments (student_id);
CREATE INDEX ix_enrollments_course ON enrollments (course_id);
CREATE INDEX ix_enrollments_status ON enrollments (status);
CREATE INDEX ix_enrollments_status_partial ON enrollments (student_id, course_id)
    WHERE status = 'pending';

CREATE TABLE results (
    id            VARCHAR(36) PRIMARY KEY,
    enrollment_id VARCHAR(36) NOT NULL UNIQUE REFERENCES enrollments(id) ON DELETE CASCADE,
    marks         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    grade         VARCHAR(2) NOT NULL DEFAULT '',
    semester      VARCHAR(16) NOT NULL DEFAULT ''
);
ALTER TABLE results ADD CONSTRAINT chk_results_marks CHECK (marks >= 0.0 AND marks <= 100.0);
ALTER TABLE results ADD CONSTRAINT chk_results_grade CHECK (grade ~ '^[A-F]$');

CREATE TABLE attendance (
    id            VARCHAR(36) PRIMARY KEY,
    enrollment_id VARCHAR(36) NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    day           DATE NOT NULL,
    status        VARCHAR(8) NOT NULL DEFAULT 'present',
    CONSTRAINT chk_attendance_status CHECK (status IN ('present', 'absent'))
);
CREATE INDEX ix_attendance_enrollment ON attendance (enrollment_id);
CREATE INDEX ix_attendance_enrollment_day ON attendance (enrollment_id, day);

-- ---------------------------------------------------------------------
-- 4. Resources & timetable
-- ---------------------------------------------------------------------
CREATE TABLE rooms (
    id       VARCHAR(36) PRIMARY KEY,
    room_no  VARCHAR(16) NOT NULL,
    capacity INT NOT NULL DEFAULT 50,
    kind     VARCHAR(32) NOT NULL DEFAULT 'classroom'
);
CREATE UNIQUE INDEX uq_rooms_room_no ON rooms (room_no);
ALTER TABLE rooms ADD CONSTRAINT chk_rooms_capacity CHECK (capacity >= 0);

CREATE TABLE timetable_entries (
    id          VARCHAR(36) PRIMARY KEY,
    course_id   VARCHAR(36) NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    room_id     VARCHAR(36) NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    lecturer_id VARCHAR(36) NOT NULL REFERENCES lecturers(id) ON DELETE RESTRICT,
    day         VARCHAR(12) NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    term        VARCHAR(16) NOT NULL DEFAULT ''
);
CREATE INDEX ix_tt_course ON timetable_entries (course_id);
CREATE INDEX ix_tt_room ON timetable_entries (room_id);
CREATE INDEX ix_tt_lecturer ON timetable_entries (lecturer_id);
CREATE INDEX ix_tt_conflict_guard ON timetable_entries (room_id, day, start_time);

-- ---------------------------------------------------------------------
-- 5. ML: models, predictions, interventions
-- ---------------------------------------------------------------------
CREATE TABLE models (
    id         VARCHAR(36) PRIMARY KEY,
    name       VARCHAR(64) NOT NULL,
    version    VARCHAR(64) NOT NULL,
    path       VARCHAR(255) NOT NULL DEFAULT '',
    metrics    JSONB NOT NULL DEFAULT '{}'::jsonb,
    trained_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE predictions (
    id            VARCHAR(36) PRIMARY KEY,
    student_id    VARCHAR(36) NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id     VARCHAR(36) NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    probability   DOUBLE PRECISION NOT NULL,
    risk_level    VARCHAR(16) NOT NULL,
    shap_values   JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version VARCHAR(64) NOT NULL DEFAULT '',
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_predictions_probability CHECK (probability >= 0.0 AND probability <= 1.0),
    CONSTRAINT chk_predictions_risk CHECK (risk_level IN ('high', 'medium', 'low'))
);
CREATE INDEX ix_predictions_student ON predictions (student_id);
CREATE INDEX ix_predictions_course ON predictions (course_id);
CREATE INDEX ix_predictions_created ON predictions (created_at DESC);
CREATE INDEX ix_predictions_payload_gin ON predictions USING GIN (shap_values);

CREATE TABLE intervention_plans (
    id                   VARCHAR(36) PRIMARY KEY,
    prediction_id        VARCHAR(36) NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    plan_text            TEXT NOT NULL,
    status               VARCHAR(16) NOT NULL DEFAULT 'drafted',
    notified_lecturer_id VARCHAR(36),
    CONSTRAINT chk_intervention_status CHECK (status IN ('drafted', 'sent', 'completed'))
);

-- ---------------------------------------------------------------------
-- 6. Governance: approvals, audit trail, decision cards
-- ---------------------------------------------------------------------
CREATE TABLE approval_requests (
    id         VARCHAR(36) PRIMARY KEY,
    user_id    VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intent     VARCHAR(64) NOT NULL,
    payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    status     VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMP,
    CONSTRAINT chk_approval_status CHECK (status IN ('pending', 'approved', 'rejected'))
);
CREATE INDEX ix_approval_status ON approval_requests (status);
CREATE INDEX ix_approval_payload_gin ON approval_requests USING GIN (payload);

CREATE TABLE audit_logs (
    id          VARCHAR(36) PRIMARY KEY,
    actor       VARCHAR(64) NOT NULL,
    action      VARCHAR(64) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id   VARCHAR(36),
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_hash   VARCHAR(64) NOT NULL,
    hash        VARCHAR(64) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uq_audit_hash ON audit_logs (hash);
CREATE INDEX ix_audit_created ON audit_logs (created_at DESC);
CREATE INDEX ix_audit_actor ON audit_logs (actor);
CREATE INDEX ix_audit_action ON audit_logs (action);
CREATE INDEX ix_audit_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_payload_gin ON audit_logs USING GIN (payload);

CREATE TABLE decision_cards (
    id            VARCHAR(36) PRIMARY KEY,
    audit_log_id  VARCHAR(36) NOT NULL REFERENCES audit_logs(id) ON DELETE CASCADE,
    decision_type VARCHAR(64) NOT NULL,
    inputs        JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning     TEXT NOT NULL,
    model_version VARCHAR(64) NOT NULL DEFAULT '',
    approver_id   VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    decided_at    TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_decision_cards_type ON decision_cards (decision_type);
CREATE INDEX ix_decision_cards_inputs_gin ON decision_cards USING GIN (inputs);

-- ---------------------------------------------------------------------
-- 7. Tamper-evident audit trigger
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION block_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only: UPDATE/DELETE is forbidden';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_append_only
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION block_audit_modification();

-- ---------------------------------------------------------------------
-- 8. Comments
-- ---------------------------------------------------------------------
COMMENT ON TABLE users IS 'Authentication and RBAC. role discriminator + optional 1:1 profile.';
COMMENT ON TABLE students IS 'Student profile (1:1 with users).';
COMMENT ON TABLE lecturers IS 'Lecturer profile (1:1 with users); max_hours feeds OR-Tools solver.';
COMMENT ON TABLE enrollments IS 'Registration records. status drives the HITL approval queue.';
COMMENT ON TABLE results IS 'Per-enrollment grade; grade is denormalized from marks.';
COMMENT ON TABLE attendance IS 'Per-enrollment daily attendance; input to ML features.';
COMMENT ON TABLE timetable_entries IS 'Solved timetable assignments (OR-Tools).';
COMMENT ON TABLE predictions IS 'ML risk scores with SHAP explanations stored inline.';
COMMENT ON TABLE audit_logs IS 'Append-only event log with SHA-256 hash chaining; trigger blocks mutation.';
COMMENT ON TABLE decision_cards IS 'Human-readable "why" record for each automated decision.';
COMMENT ON TABLE models IS 'ML registry mirror pointing at MLflow artifact paths.';

COMMIT;
