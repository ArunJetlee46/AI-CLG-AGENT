# PHASE 1 — Requirement Analysis

## Beru Campus AI — Autonomous Multi-Agent University Operating System

> **Tagline:** "An AI workforce that autonomously manages academic operations, predicts student success, and optimizes campus resources through collaborative AI agents."

| Field | Value |
|---|---|
| Project Title | Beru Campus AI – Autonomous Multi-Agent University Operating System |
| Project Type | Final Year Project (FYP) |
| Phase | Phase 1 — Requirement Analysis |
| Document Version | 1.0 |
| Status | Draft |
| Last Updated | 2026-08-11 |

---

## 1. Problem Statement

Universities run on fragmented, manually operated systems. Academic operations (registration, grading, attendance, scheduling) live in separate silos; student success is only detected reactively — after a student has already failed or dropped out; and campus resources (classrooms, labs, staff time) are allocated by static rules that ignore real usage. Consequences include:

1. **Manual administrative load** — staff spend hours on repetitive tasks (querying transcripts, drafting timetables, chasing attendance, generating reports) instead of high-value work.
2. **Reactive student support** — at-risk students are identified too late; interventions are generic, not evidence-based.
3. **Wasted resources** — under-utilized classrooms/labs, overlapping bookings, and sub-optimal lecturer timetables.
4. **Non-transparent AI** — AI recommendations cannot be trusted or audited because decisions lack explanation and traceability.
5. **No integrated view** — no single system links academic records, student performance, and resource usage to answer cross-domain questions (e.g., "will this timetable change hurt these students?").

**Beru Campus AI** addresses this by acting as an *autonomous AI workforce*: a system of specialized AI agents that collaborate to operate routine academic processes, predict student outcomes, and optimize resource allocation — while keeping every decision explainable, auditable, and under human supervision.

---

## 2. Scope

### 2.1 In Scope

- Autonomous execution of core academic operations workflows via collaborative LLM agents (orchestrated with LangGraph):
  - Student registration & enrollment support
  - Course catalog queries (RAG over institutional documents)
  - Attendance tracking & reporting
  - Grade management & transcript queries
- **Student Success Prediction**: ML models (XGBoost / LightGBM) predicting at-risk students, with SHAP/LIME explanations.
- **Resource Optimization**: OR-Tools based timetabling and classroom/lecturer allocation optimization.
- **Knowledge Graph**: entity-relationship model (students, courses, lecturers, rooms, departments) in Neo4j powering cross-domain reasoning.
- **Synthetic Data Generator**: deterministic, privacy-safe synthetic university dataset (GDPR-compliant generation) to train, test, and demo the system.
- **Audit Trail Agent**: immutable, searchable log of every agent action, LLM prompt/response, model prediction, and human approval — for accountability and compliance.
- **Auth & Roles**: JWT-based authentication (python-jose + passlib/bcrypt) with RBAC (Student, Lecturer, Admin).
- **Human-in-the-loop (HITL)**: approval gates for high-impact actions (e.g., grade changes, registration overrides).
- **Frontend Dashboard**: React + Vite + shadcn/ui with role-specific views (student portal, staff console, admin command center) and Recharts visualizations.

### 2.2 Out of Scope

- Real payment/billing or full financial systems.
- Integration with the university's legacy SIS/ERP (a stubbed API adapter is provided instead).
- Mobile native apps (responsive web only).
- Real-time campus IoT / physical access control.
- Multilingual support (English-only for v1).
- Legal-grade archiving or official transcript issuance (audit trail is demonstrative, not legally binding).

### 2.3 Assumptions & Constraints

- Uses only the approved **free-tier stack** (Groq/Gemini/Ollama LLMs, self-hosted Postgres/Redis/Qdrant/Neo4j via Docker Compose; Render/Vercel free tiers).
- All data used for training/demo is synthetic or anonymized; no real student PII is stored.
- Runs as a demonstrative prototype on a single server / laptop for evaluation (FYP defense), with architecture ready to scale.

---

## 3. Functional Requirements

Priorities: **M** = Must, **S** = Should, **C** = Could, **W** = Won't (this release).

### FR-1 Authentication & Access Control

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | System shall support registration and JWT-based login for Students, Lecturers, and Admins. | M |
| FR-1.2 | System shall enforce role-based access control (RBAC): students see own data only; lecturers see their courses; admins see all. | M |
| FR-1.3 | System shall support password hashing with bcrypt and token expiry/refresh. | M |

### FR-2 Academic Operations Agent

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Agent shall answer course-catalog and policy questions via RAG over institutional documents (LangGraph + Qdrant). | M |
| FR-2.2 | Agent shall guide a student through course registration and validate prerequisites against the knowledge graph. | M |
| FR-2.3 | Agent shall auto-generate attendance and grade reports on request. | S |
| FR-2.4 | High-impact actions (registration override, grade correction) shall require an Admin approval before execution. | M |

### FR-3 Student Success Prediction Agent

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | System shall train & serve models (XGBoost / LightGBM) predicting risk of failure/dropout per student per course. | M |
| FR-3.2 | System shall generate SHAP/LIME explanations for each prediction (feature contributions). | M |
| FR-3.3 | Agent shall draft a personalized intervention plan (e.g., tutoring referral) and notify the student's lecturer. | S |

### FR-4 Resource Optimization Agent

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | System shall solve timetable assignment with Google OR-Tools (lecturer conflicts, room capacity, time-slot constraints). | M |
| FR-4.2 | System shall detect room/lecturer conflicts and propose conflict-free alternatives. | S |
| FR-4.3 | Agent shall report utilization metrics (room occupancy %, load balancing) to admins. | S |

### FR-5 Knowledge Graph & RAG

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | System shall maintain entities (Student, Course, Lecturer, Room, Department, Enrollment, Result) and relationships in Neo4j. | M |
| FR-5.2 | System shall answer cross-domain queries (e.g., "lecturers overloaded this semester", "students who failed CS201 twice") via Cypher + LLM natural-language interface. | S |
| FR-5.3 | Vector store (Qdrant) shall index institutional documents for retrieval-augmented answering. | M |

### FR-6 Synthetic Data Generator

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | Generator shall produce realistic, schema-consistent synthetic data for students, courses, lecturers, enrollments, grades, attendance, and room schedules. | M |
| FR-6.2 | Generator shall embed realistic failure/dropout patterns so prediction models can be validated. | M |
| FR-6.3 | Generator shall support configurable dataset size (e.g., 500 / 5,000 / 50,000 students) via CLI and API. | S |
| FR-6.4 | Generated data shall be fully synthetic (no real PII) and flagged as synthetic in the knowledge graph. | M |

### FR-7 Audit Trail Agent

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Every agent action, LLM call (model, prompt hash, response), prediction, and human approval shall be recorded with timestamp and actor. | M |
| FR-7.2 | Audit log shall be queryable/filterable (actor, action type, entity, date range) and exportable to CSV. | M |
| FR-7.3 | Audit records shall be append-only and tamper-evident (hash-chaining). | S |
| FR-7.4 | A "Decision Card" shall summarize why each automated decision was made (inputs, model, explanation, approval). | S |

### FR-8 Frontend & Monitoring

| ID | Requirement | Priority |
|---|---|---|
| FR-8.1 | Dashboard shall provide role-based views: Student Portal, Lecturer Console, Admin Command Center. | M |
| FR-8.2 | Dashboard shall visualize predictions (risk scores), resource utilization, and audit activity with Recharts. | S |
| FR-8.3 | System shall expose /metrics for Prometheus and forward errors to Sentry. | C |

---

## 4. Non-Functional Requirements

| Category | Requirement | Target / Measure |
|---|---|---|
| Performance | Agent API response time (LLM-backed endpoints) | p95 < 5s (LLM streaming), non-LLM APIs p95 < 500ms |
| Performance | Prediction inference latency | < 200ms per student |
| Performance | Timetable optimization | solve ≤ 500 courses / 2,000 slots in < 5 min |
| Scalability | Horizontal scaling of stateless API + workers | Celery workers scale with Redis queue; async endpoints |
| Reliability | Uptime for demo/defense environment | ≥ 99% during evaluation window |
| Availability | Graceful degradation if external LLM (Groq/Gemini) is down | Automatic fallback to local Ollama model |
| Security | Auth | JWT with refresh; bcrypt hashing; RBAC enforced server-side |
| Security | Data protection | No real PII; synthetic data only; secrets via env vars / .env (never committed) |
| Security | Input safety | LLM prompt injection mitigation (system prompts + output validation) |
| Auditability | Every automated decision traceable | 100% of agent actions logged with Decision Cards |
| Usability | Dashboard usable by non-technical staff | Task success rate ≥ 90% in informal evaluation; WCAG AA basic contrast |
| Maintainability | Modular monorepo, typed code, CI | GitHub Actions runs lint + tests; all services containerized |
| Portability | Deployment | docker compose up on any machine; Render/Vercel free tiers for hosting |
| Explainability | Every ML prediction includes explanation | SHAP/LIME attached to prediction records |
| Cost | Must stay within free tiers | Zero cloud spend; LLM API quotas respected with local fallback |
| Extensibility | New agents pluggable | LangGraph graph definition allows adding agents without core changes |

---

## 5. Stakeholders

| Stakeholder | Role in Project | Key Concerns |
|---|---|---|
| FYP Student (Developer) | Architect, developer, evaluator | Feasibility, academic merit, scope control, defense readiness |
| FYP Supervisor | Academic advisor | Rigor, originality, alignment with objectives, documentation quality |
| FYP Examiner / Defense Panel | Evaluator | Technical depth, working demo, understanding of design trade-offs |
| University Administrator | User persona (target user) | Efficiency, reliability, oversight & control of automated actions |
| Lecturer | User persona | Correctness of schedules/grades, reduced admin burden, student insights |
| Student | User persona | Fast answers, transparency of decisions affecting them, data privacy |
| IT/DevOps (hypothetical) | Operator | Deployability, monitoring, security, cost |
| Ethics/Data Protection Officer (hypothetical) | Compliance advisor | Privacy of student data, auditability, fairness of predictions |

---

## 6. Use Cases

### UC-01 — Student Self-Service Query (RAG)
- **Actor:** Student
- **Precondition:** Authenticated student
- **Flow:** Student asks "What are the prerequisites for CS202?" → RAG agent retrieves from Qdrant → LLM answers with cited sources.
- **Postcondition:** Answer with citations; action logged to audit trail.
- **Priority:** M

### UC-02 — Guided Course Registration
- **Actor:** Student; **Admin (approver)** for overrides
- **Flow:** Student selects courses → agent validates capacity, timetable clash, prerequisites (knowledge graph) → confirms registration → audit + notification.
- **Alternate:** Prerequisite/clash detected → agent suggests alternatives or requests admin override.
- **Priority:** M

### UC-03 — At-Risk Student Prediction & Alerting
- **Actor:** Lecturer, Admin
- **Flow:** Prediction agent scores students (mid-term) → risk list with SHAP explanations → intervention plan drafted → lecturer notified via dashboard.
- **Postcondition:** Decision Cards stored in audit trail.
- **Priority:** M

### UC-04 — Automatic Timetable Generation
- **Actor:** Admin
- **Flow:** Admin submits course/room/lecturer constraints → OR-Tools solves → conflict report + utilization metrics → admin approves or regenerates.
- **Priority:** S

### UC-05 — Cross-Domain Query via Knowledge Graph
- **Actor:** Admin
- **Flow:** Admin asks "Which lecturers are overloaded and which of their courses have high failure risk?" → LLM translates to Cypher → Neo4j returns → natural-language answer + graph view.
- **Priority:** S

### UC-06 — Audit Review & Compliance Report
- **Actor:** Admin
- **Flow:** Admin filters audit log (actor, action, date) → reviews Decision Cards → exports CSV report.
- **Priority:** S

### UC-07 — Synthetic Dataset Generation
- **Actor:** Admin / Developer
- **Flow:** Admin triggers generator (CLI/API) with size + seed → generator produces schema-consistent dataset → loads into Postgres/Neo4j/Qdrant with synthetic flag.
- **Priority:** M

### UC-08 — Human Approval Gate (HITL)
- **Actor:** Admin
- **Flow:** Agent requests high-impact action → Admin approves/rejects via dashboard → action executes only on approval; both paths audited.
- **Priority:** M

---

## 7. User Stories

### Epic A — Student Experience
- As a **student**, I want to ask course questions in plain language, so I get instant answers with citations.
- As a **student**, I want to register for courses with automatic prerequisite/clash checks, so I avoid schedule errors.
- As a **student**, I want to see my progress and risk status, so I can act before it's too late.

### Epic B — Academic Operations
- As a **lecturer**, I want attendance and grade reports auto-generated, so I spend less time on admin.
- As a **lecturer**, I want risk alerts for my students with explanations, so I can intervene effectively.
- As an **admin**, I want a timetable that avoids conflicts automatically, so I don't resolve clashes manually.

### Epic C — Institutional Intelligence
- As an **admin**, I want cross-domain questions answered from the knowledge graph, so I get insights without SQL.
- As an **admin**, I want utilization metrics, so I can reallocate underused rooms/staff.

### Epic D — Trust & Governance
- As an **admin**, I want every automated decision logged with a Decision Card, so I can justify actions to stakeholders.
- As an **admin**, I want role-based access and approval gates, so no system can act beyond policy.

### Epic E — Data & Evaluation
- As a **developer**, I want a deterministic synthetic data generator, so I can demo and test without real student data.
- As a **developer**, I want to reproduce any model result from a logged config, so I can defend the work in evaluation.

---

## 8. Project Modules

```
Beru Campus AI
│
├── M1  API Gateway & Auth (FastAPI, JWT, RBAC)
├── M2  Agent Orchestration (LangGraph supervisor + sub-agents)
│      ├── A1 Academic Operations Agent (registration, reports, RAG)
│      ├── A2 Student Success Agent (predictions + interventions)
│      ├── A3 Resource Optimization Agent (OR-Tools timetabling)
│      └── A4 Knowledge & Query Agent (Neo4j Cypher + RAG)
├── M3  Synthetic Data Generator (CLI + API, seeded, privacy-safe)
├── M4  Audit Trail Agent (append-only, hash-chained, Decision Cards)
├── M5  ML Pipeline (scikit-learn/XGBoost/LightGBM + SHAP/LIME, MLflow)
├── M6  Data Layer (PostgreSQL, Neo4j, Qdrant, Redis)
├── M7  Async Task Queue (Celery + Redis)
├── M8  Frontend (React + Vite, shadcn/ui, Zustand/React Query, Recharts)
├── M9  Observability (Prometheus, Grafana, Sentry)
└── M10 DevOps (Docker Compose, GitHub Actions CI/CD)
```

### Module Descriptions

| Module | Responsibility | Key Technologies |
|---|---|---|
| M1 API Gateway & Auth | All HTTP entry points; JWT issuance/validation; RBAC middleware; request routing to agents | FastAPI, python-jose, passlib/bcrypt |
| M2 Agent Orchestration | Supervisor graph routes intents to specialist agents; maintains shared state; enforces HITL gates | LangGraph, Groq/Gemini/Ollama (fallback), LangChain |
| A1 Academic Ops Agent | Registration flows, report generation, policy Q&A with citations | Qdrant, bge-small-en embeddings, bge-reranker |
| A2 Student Success Agent | Loads features, scores risk, builds SHAP explanation, drafts intervention | XGBoost/LightGBM, SHAP/LIME, MLflow |
| A3 Resource Optimization Agent | Constraint modeling, solver invocation, conflict/utilization reporting | Google OR-Tools |
| A4 Knowledge & Query Agent | NL→Cypher translation, graph traversal, entity linking | Neo4j, LLM |
| M3 Synthetic Data Generator | Deterministic generation of students/courses/enrollments/grades/attendance/rooms with embedded failure patterns; loads all stores | Python (Faker-style logic, seeded RNG) |
| M4 Audit Trail Agent | Intercepts every agent action, LLM call, prediction, approval; append-only log with hash chaining; Decision Card builder; CSV export | PostgreSQL (append-only tables), FastAPI events |
| M5 ML Pipeline | Feature engineering, model training/eval/registry, prediction serving, explainability | scikit-learn, XGBoost, LightGBM, SHAP, LIME, MLflow |
| M6 Data Layer | Relational source of truth; graph; vector index; cache | PostgreSQL, Neo4j, Qdrant, Redis |
| M7 Async Queue | Long-running tasks (generation, training, timetabling, notifications) off HTTP path | Celery + Redis |
| M8 Frontend | Role dashboards; agent chat; prediction & utilization charts; audit viewer | React, Vite, shadcn/ui, Tailwind, Zustand, React Query, Recharts |
| M9 Observability | Metrics, dashboards, error tracking | Prometheus, Grafana, Sentry |
| M10 DevOps | One-command local deployment; CI on push | Docker, Docker Compose, GitHub Actions |

---

## 9. Success Criteria / KPIs

| Criterion | Measure |
|---|---|
| Autonomous operation | ≥ 80% of scripted academic-operation tasks completed without human step-in |
| Prediction quality | AUC-ROC ≥ 0.85 on synthetic hold-out set; SHAP attached to 100% of served predictions |
| Resource optimization | ≥ 20% reduction in timetable conflicts vs. naive allocation (demo scenario) |
| Audit completeness | 100% of automated decisions have a Decision Card |
| Explainability | 100% of predictions include human-readable explanation |
| Reliability | Fallback to local LLM verified (network-off test) |
| Defense readiness | Full end-to-end demo script runnable in < 15 minutes on one laptop |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Free-tier LLM quota exhaustion | High | Local Ollama fallback; request caching; batch prompts |
| Scope creep (many agents) | High | Strict phase gating; each phase ends with working demo |
| Neo4j/Qdrant resource usage on laptop | Medium | Lightweight profiles; seed small datasets; optional ChromaDB fallback |
| Prediction quality on synthetic data is not "real" | Medium | State clearly in report; validate patterns statistically |
| Language model hallucination in answers | Medium | RAG citations; deterministic rule checks before execution; HITL gates |
| Deployment free-tier limits (cold starts, sleep) | Low | Docker for defense; pre-warm before demo |
| Grade changes / wrong automated actions | High | Never auto-execute high-impact actions; approval required + audit |

---

## 11. Appendix — Tech Stack Mapping (per approved stack)

| Concern | Tool |
|---|---|
| Agent reasoning | Groq (Llama 3.3 70B / 3.1 8B) or Gemini Flash; fallback: Ollama (Llama 3.1 8B / Phi-3) |
| Embeddings | BAAI/bge-small-en-v1.5 (local); reranker bge-reranker-base |
| Orchestration | LangGraph |
| Backend | FastAPI; Celery + Redis; python-jose; passlib (bcrypt) |
| Databases | PostgreSQL, Neo4j CE, Qdrant (fallback ChromaDB), Redis |
| ML | scikit-learn, XGBoost, LightGBM; SHAP, LIME; OR-Tools; MLflow |
| Frontend | React + Vite, shadcn/ui, Tailwind CSS, Zustand/React Query, Recharts |
| DevOps | Docker Compose, GitHub Actions, Prometheus + Grafana, Sentry |
| Hosting | Render/Fly.io (backend), Vercel/Netlify (frontend) |

---

## 12. Next Steps (Phase 2 Preview)

1. Monorepo scaffold (backend, frontend, docker-compose).
2. Synthetic Data Generator (M3) — first vertical slice.
3. Postgres schema + Neo4j graph model + Qdrant collection setup.
4. LangGraph skeleton with 2 agents and audit interceptor.
