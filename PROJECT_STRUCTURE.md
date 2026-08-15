# Beru Campus AI — Project Structure & Features

> "An AI workforce that autonomously manages academic operations, predicts student success, and optimizes campus resources through collaborative AI agents."

## System overview

```
┌─────────────┐   /api (vite proxy)   ┌──────────────┐
│  frontend   │ ────────────────────► │  backend     │
│  React/Vite │  http://localhost:5173│  FastAPI     │
│  :5173      │ ◄──────────────────── │  :8000       │
└─────────────┘                       └──────┬───────┘
                                             │
                  ┌─────────────┬────────────┼─────────────┬──────────────┐
                  ▼             ▼            ▼             ▼              ▼
             ┌──────────┐  ┌──────────┐ ┌─────────┐  ┌───────────┐  ┌────────────┐
             │  Ollama  │  │ SQLite/  │ │ ChromaDB│  │ curriculum│  │ (optional) │
             │  :11434  │  │ Postgres │ │ /Qdrant │  │ RAG (in-  │  │ Celery/Redis│
             └──────────┘  └─────────┘  └─────────┘  │ process)  │  └────────────┘
                                                     └──────────┘
```

## Roles & demo logins

| Role | Username | Password | Home route |
|---|---|---|---|
| Student | `student` | `student123` | `/student` (My Space) |
| Faculty (Lecturer) | `lecturer` | `lecturer123` | `/faculty` |
| Placement Officer | `placement` | `placement123` | `/placement` |
| Administrator | `admin` | `admin123` | `/admin` (Command Center) |

Role model: `student` / `lecturer` / `placement` / `admin` (granular RBAC via `require_role(...)` per route).

## Features

### 🤖 Core platform
- **Multi-agent orchestration (LangGraph)**: Supervisor → specialist agents (Advising, Success, Resource) → Execute Agent. Specialists are **propose-only**; the **Execute Agent is the only writer**.
- **Human-in-the-loop approvals**: every mutating operation requires an approved `ApprovalRequest` (`require_approved` gate).
- **Immutable audit trail**: hash-chained `AuditLog` carrying the `approval_id` that authorized each write.
- **LLM gateway with fallback**: Groq → Gemini → Ollama (`llama3.2:3b`) → local refusal fallback. Provider-aware responses (`provider` + `model`).
- **Hybrid RAG**: keyword + vector retrieval (Chroma/Qdrant) with grounded answers and citations; `provider: "college-ai"` curriculum RAG in-process.
- **Synthetic data generator**: deterministic 500-student / 40-course dataset (`python -m synthetic.cli`).
- **Prerequisite CTE traversal**: recursive-CTE prerequisite chain with eligibility advising.
- **ML pipeline**: feature datasets, dropout/placement/attendance/performance heuristics, sklearn model training + SHAP explanations, OR-Tools timetable optimization.
- **Observability**: Prometheus `/metrics` + Grafana dashboards; secure-boot guard (refuses production boot with default creds).

### 🎓 Student Copilot (`/student`)
- Success score (0–100) + risk band + drivers.
- Early warnings (attendance <75%, F grades, unmet prerequisites).
- Predicted pass probability per course (`heuristic-v1`) + projected GPA.
- Daily priority plan + Personal AI Advisor (prerequisite-aware eligibility).

### 🏫 Faculty Copilot (`/faculty`)
- Workload profile (courses, students, teaching hours).
- Class performance intelligence (avg/high/low, pass rate, strong/average/at-risk bands, trend flags).
- At-risk monitor with explainable reasons.
- Course health score (0–100) + attendance report (<75% below threshold).
- **Approval-gated interventions**: propose → lecturer approves → Execute Agent persists plan + audit.

### 💼 Placement Copilot (`/placement`)
- Placement readiness score (0–100) with band (Ready / Needs Improvement / Not Ready) + components + drivers.
- Batch overview: predicted placement rate, department comparison, funnel.
- Unplaced-risk monitor with reasons.
- **AI job–student shortlisting**: GPA + backlog gates, match-score ranking.
- One-click batch report.

### 🏛️ Admin Copilot (`/admin` — University Command Center)
- Command center: counts (students/faculty/departments/courses) + KPIs + pending approvals + system health.
- **University Health Score** (0–100) across 5 weighted axes (academic, student success, placement, faculty, AI operations).
- **Early Warning System**: dropout-risk, attendance, weak courses, placement-readiness — each with a recommendation.
- **Department Intelligence**: health scores per department + flags.
- **Faculty workload** analytics.
- **Agent Control Center**: 7 agents with tasks processed / status derived from the audit log.
- **Emergency Kill Switch**: `POST /admin/safety` pauses AI execution or enables read-only mode; the Execute Agent rejects every write at the source while paused.

## Root level

```
ai pro/
├── backend/            # FastAPI backend (port 8000) — main API + agents + ML + in-process curriculum RAG
├── frontend/           # React + Vite SPA (port 5173)
├── data/               # Shared knowledge corpus (Beru's RAG KB + curriculum corpus + course index)
├── deploy/             # Prometheus, Grafana, SQL schema, Neo4j seed
├── docs/               # 13 phase design documents
├── .github/            # CI workflows
├── .env / .env.example # Environment configuration
├── docker-compose.yml  # Full mode: postgres, redis, neo4j, qdrant, mlflow, backend, worker, frontend (+ observability/ollama profiles)
├── docker-compose.local.yml
├── fly.toml            # Fly.io deployment
├── render.yaml         # Render deployment
├── netlify.toml        # Netlify deployment
├── PROJECT_STRUCTURE.md
└── README.md
```

## backend/ — FastAPI application

```
backend/
├── app/
│   ├── main.py                 # App factory, secure boot guard, admin/demo-user/KB/curriculum seeding, /metrics
│   ├── config.py               # All env settings (curriculum_rag_* + vector_collection, demo_student_id, demo_lecturer_id)
│   ├── db.py                   # SQLAlchemy engine, SessionLocal, init_db + schema migrations
│   ├── agents/                 # LangGraph multi-agent orchestration
│   │   ├── supervisor.py       # Intent router → routes to a specialist agent
│   │   ├── specialists.py      # Advising / Success / Resource agents (propose-only)
│   │   ├── academic_ops.py     # Advising agent: RAG answers + prerequisite validation
│   │   ├── execute.py          # Execute Agent — the ONLY writer in the system
│   │   ├── base.py             # Shared agent base class
│   │   ├── state.py            # Agent state schemas
│   │   ├── memory.py           # Conversation memory helpers
│   │   ├── debate.py           # Multi-agent debate helper
│   │   └── __init__.py
│   ├── api/
│   │   ├── deps.py             # Auth/DB dependencies (get_current_user, require_role)
│   │   └── routes/
│   │       ├── health.py       # GET /api/v1/health
│   │       ├── auth.py         # login/refresh (JWT + bcrypt)
│   │       ├── agents.py       # POST /api/v1/agents/chat, run, review
│   │       ├── approvals.py    # Approve/execute gated writes (admin + lecturer-decides-own-interventions)
│   │       ├── audit.py        # Hash-chained audit log queries
│   │       ├── predictions.py  # Risk predictions + SHAP explanations (admin/lecturer/placement)
│   │       ├── students.py     # GET /api/v1/students/me, success-score, alerts, predictions, today, advise
│   │       ├── faculty.py      # GET /api/v1/faculty/me, overview, at-risk, courses/{code}/health,
│   │       │                   #   courses/{code}/attendance, POST/GET interventions
│   │       ├── placement.py    # GET /api/v1/placement/overview, readiness, at-risk, report; POST shortlist
│   │       ├── admin_module.py # GET /api/v1/admin/command-center, health-score, early-warnings,
│   │       │                   #   departments, faculty-workload, agents, safety; POST safety
│   │       └── synthetic.py    # Synthetic data generation API
│   ├── core/
│   │   ├── security.py         # JWT, bcrypt password hashing
│   │   ├── approvals.py        # ApprovalRequest model logic (require_approved gate)
│   │   ├── audit.py            # Audit trail with approval_id + hash chain
│   │   ├── safety.py           # Emergency kill switch state (execution_allowed gate)
│   │   └── exceptions.py       # AppError + handlers + request context middleware
│   ├── ml/
│   │   ├── datasets.py         # Feature datasets (cached ~300s TTL)
│   │   ├── features.py         # Feature engineering
│   │   ├── models.py           # Model registry
│   │   ├── train.py            # Training entrypoints
│   │   ├── predict.py          # Dropout-risk heuristic + predictions
│   │   ├── optimize.py         # OR-Tools timetable optimization
│   │   └── cli.py              # ML CLI
│   ├── models/
│   │   └── entities.py         # SQLAlchemy entities (users, students, lecturers, courses, enrollments,
│   │                           #   results, attendance, audit_logs, approvals, InterventionPlan, etc.)
│   ├── schemas/
│   │   └── common.py           # Pydantic contracts (incl. AdviseRequest, InterventionRequest, ShortlistRequest)
│   ├── services/
│   │   ├── llm.py              # LLM gateway: Groq → Gemini → Ollama → local fallback
│   │   ├── rag.py              # RAG answer pipeline + curriculum fallback (_ask_curriculum_rag)
│   │   ├── curriculum_rag.py   # In-process curriculum KB (merged from college-ai): hybrid
│   │   │                       #   retriever + grounding engine (229 chunks)
│   │   ├── vector_store.py     # Qdrant/Chroma backends, main + curriculum collections, has()
│   │   ├── pipeline.py         # KB ingestion (main + curriculum, idempotent)
│   │   ├── evaluation.py       # Grounded-answer evaluation/refusal markers
│   │   ├── execution.py        # Approved write execution (guarded by safety kill switch)
│   │   ├── prereqs.py          # Recursive-CTE prerequisite traversal
│   │   ├── students.py         # Student Copilot logic (score, alerts, predictions, advise, today)
│   │   ├── faculty.py          # Faculty Copilot logic (workload, health, at-risk, interventions)
│   │   ├── placement.py        # Placement Copilot logic (readiness, at-risk, shortlist, report)
│   │   ├── admin_copilot.py    # Admin Copilot logic (command center, health score, early warnings, agents)
│   │   └── graph_service.py    # Knowledge graph helpers
│   └── workers/
│       ├── celery_app.py       # Celery app
│       └── tasks.py            # Background tasks
├── finetuning/                 # Offline LoRA/QLoRA training (moved from college-ai)
│   ├── train.py                # LoRA/QLoRA training script
│   ├── generate_finetune_dataset.py  # curriculum → train/validation JSONL
│   ├── train.jsonl / validation.jsonl
│   └── Modelfile.ft            # Ollama Modelfile for the fine-tuned assistant
├── synthetic/
│   ├── cli.py                  # CLI entry: python -m synthetic.cli
│   └── generator.py            # Deterministic synthetic data generator
├── scripts/
│   ├── eval_rag.py             # RAG evaluation script
│   └── load_test.py            # Load test script
├── tests/                      # 15 test files — 111 tests, all green
│   ├── conftest.py             # Isolated temp DB; CURRICULUM_RAG_ENABLED=false
│   ├── test_agent_nodes.py, test_ai_eval.py, test_api.py,
│   ├── test_approval_structural.py, test_curriculum_rag.py, test_health.py,
│   ├── test_ml.py, test_optimize.py, test_orchestration.py, test_prereqs.py,
│   ├── test_rag.py, test_students.py, test_faculty.py, test_placement.py,
│   └── test_admin_module.py
├── requirements.txt            # Core deps
├── requirements-ml.txt         # ML extras (ortools, shap, sklearn, scipy)
├── pyproject.toml              # pytest config (addopts = "-q")
├── Dockerfile
└── beru.db                     # Local SQLite database
```

## frontend/ — React SPA (port 5173)

```
frontend/
├── src/
│   ├── main.tsx                 # React entry + router (composes per-module routes, role-gated)
│   ├── index.css                # Tailwind + design tokens (.app-bg, .card-shell, .fade-up)
│   ├── core/                    # Shared platform layer (role-agnostic)
│   │   ├── lib/
│   │   │   ├── api.ts           # HTTP client + shared typed APIs (auth, chat, audit, prediction, approval, health)
│   │   │   ├── routes.ts        # ModuleRoute type ({ path, element, roles? })
│   │   │   └── utils.ts         # cn() helper
│   │   ├── stores/
│   │   │   └── auth.ts          # Zustand auth store
│   │   └── components/
│   │       ├── Layout.tsx       # App shell/navigation (role-aware nav items, user footer)
│   │       ├── ProtectedRoute.tsx  # Auth + role guard
│   │       ├── PageHeader.tsx   # Consistent page title + icon + action slot
│   │       ├── StatCard.tsx     # Reusable KPI card (icon tile + label/value/sub)
│   │       └── ui/              # shadcn/ui: badge, button, card, input
│   └── modules/                 # Per-role domain modules (each owns pages + API slice + routes)
│       ├── common/              # Shared pages used across roles
│       │   ├── Login.tsx, Dashboard.tsx, Chat.tsx, Audit.tsx, AnalyticsDashboard.tsx
│       │   └── routes.tsx
│       ├── student/             # Student Copilot (roles: student)
│       │   ├── StudentDashboard.tsx  # score gauge, alerts, pass pills, advisor
│       │   ├── api.ts               # studentApi + types
│       │   └── routes.tsx
│       ├── faculty/             # Faculty Copilot (roles: lecturer, admin)
│       │   ├── FacultyDashboard.tsx # workload, health, risk monitor, interventions
│       │   ├── api.ts               # facultyApi + types
│       │   └── routes.tsx
│       ├── placement/           # Placement Copilot (roles: placement, lecturer, admin)
│       │   ├── PlacementDashboard.tsx # command center, readiness, shortlisting
│       │   ├── api.ts               # placementApi + types
│       │   └── routes.tsx
│       └── admin/               # Admin Copilot — University Command Center (role: admin)
│           ├── AdminDashboard.tsx   # health score, warnings, agents, kill switch
│           ├── api.ts               # adminApi + types
│           └── routes.tsx
├── index.html
├── vite.config.ts               # Vite proxy /api → http://localhost:8000
├── package.json                 # React 18, Vite 5, Tailwind 4, Zustand, Recharts, shadcn/ui
├── tsconfig.json
├── Dockerfile, nginx.conf, vercel.json
└── dist/                        # Build output
```

## data/ — shared knowledge base

```
data/
├── anna_university_aids_reg2021_rag.jsonl     # Beru's RAG corpus AND the curriculum RAG corpus (pre-chunked, 229 chunks)
├── anna_university_aids_reg2021_clean.txt     # raw curriculum text
└── course_index.json                          # course catalog (241 courses, code/title/page)
```

## deploy/ — observability & infra

```
deploy/
├── prometheus.yml                             # Prometheus scrape config
├── schema.sql                                 # Canonical SQL schema
├── grafana/
│   ├── dashboards/beru-overview.json
│   └── provisioning/                          # datasources + dashboards YAML
└── neo4j/seed.cypher                          # Neo4j knowledge-graph seed
```

## docs/ — design documentation

```
docs/
├── PHASE1_Requirement_Analysis.md
├── PHASE2_System_Design.md
├── PHASE3_Database_Design.md
├── PHASE4_Knowledge_Graph.md
├── PHASE5_Backend_Development.md
├── PHASE6_RAG_System.md
├── PHASE7_AI_Agent_Design.md
├── PHASE8_LangGraph_Orchestration.md
├── PHASE9_Machine_Learning.md
├── PHASE10_Timetable_Optimization.md
├── PHASE11_Frontend.md
├── PHASE12_Testing.md
└── PHASE13_Deployment.md
```

## Governance architecture (approval → execute → audit)

```
SPECIALIST AGENT (propose-only)
        │
        ▼
  RECOMMENDATION  ──►  APPROVAL REQUEST (pending)
        │                        │
        ▼                        ▼
  ADMIN / LECTURER          SAFETY GATE (kill switch)
  APPROVE / REJECT          execution_allowed?
        │                        │
        └──────────┬─────────────┘
                   ▼
          EXECUTE AGENT (only writer)
                   │
                   ▼
              AUDIT LOG (hash chain + approval_id)
```

## Key integration points

| From | To | How |
|---|---|---|
| frontend `:5173` | backend `:8000` | Vite proxy `/api` → `http://localhost:8000` |
| backend `:8000` | Ollama `:11434` | LLM gateway (llama3.2:3b, `nomic-embed-text`) |
| backend `:8000` | curriculum RAG | In-process fallback: no evidence OR LLM refuses → `provider: "college-ai"` |
| curriculum RAG | backend `:8000` | Shares the LLM gateway + embedder; own Chroma collection `curriculum_documents` |
| backend `:8000` | SQLite `beru.db` | Data persistence (Postgres in Docker full mode) |
| backend `:8000` | Qdrant/Chroma | Vector stores: main `beru_documents` + `curriculum_documents` collections |
| approvals → writes | audit log | Every mutating op is approval-gated, safety-checked, and audited with `approval_id` |

## Running the project

```bash
# Backend (port 8000) — embeds both KB + curriculum collections on first boot (idempotent)
cd backend && .venv\Scripts\activate && uvicorn app.main:app

# Frontend (port 5173)
cd frontend && npm install && npm run dev

# Ollama (models: llama3.2:3b, nomic-embed-text)
ollama serve

# Tests (111 tests)
cd backend && pytest
```

## Ports summary

| Service | Port | URL |
|---|---|---|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://127.0.0.1:8000/api/v1/health |
| Ollama | 11434 | http://localhost:11434 |
