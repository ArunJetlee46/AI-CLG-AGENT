# Beru Campus AI — Autonomous Multi-Agent University Operating System

> **"An AI workforce that autonomously manages academic operations, predicts student success, and optimizes campus resources through collaborative AI agents."**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-3178C6.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B6B.svg)](https://langchain-ai.github.io/langgraph)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Final Year Project](https://img.shields.io/badge/Final%20Year%20Project-Showcase-orange.svg)](#)

---

## 🎯 Project Highlights

| Feature | Description |
|---------|-------------|
| **🤖 Multi-Agent System** | LangGraph supervisor with 4 specialist agents (Academic Ops, Student Success, Resources, Knowledge) + reflection & debate nodes |
| **📊 Student Success Analytics** | Real-time success scoring, risk prediction, early warnings, personalized study plans |
| **🎓 Faculty AI Copilot** | Question paper generation, lesson plans, assignment evaluation, code review, viva questions |
| **💼 Placement Intelligence** | JD analysis, candidate matching, drive management, funnel analytics, salary trends |
| **🔍 Hybrid RAG Pipeline** | Keyword + vector search + curriculum-specific RAG with citations |
| **📈 ML Pipeline** | XGBoost/LightGBM with MLflow tracking, SHAP explainability, drift monitoring |
| **🔐 Production-Ready Auth** | JWT + refresh tokens, RBAC, audit logging with hash-chained integrity |

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Agent Orchestration** | LangGraph (supervisor → planner → specialists → reflect → debate → terminal) |
| **LLM Gateway** | Groq (Llama 3.3 70B) → Gemini Flash → Ollama (local fallback) |
| **Embeddings** | BAAI/bge-small-en-v1.5 (local); bge-reranker-base |
| **Backend** | FastAPI, Celery + Redis, python-jose, passlib (bcrypt) |
| **Databases** | PostgreSQL (primary), Neo4j (graph), Qdrant (vectors), Redis (cache/queue) |
| **ML/Ops** | scikit-learn, XGBoost, LightGBM, SHAP, OR-Tools, MLflow |
| **Frontend** | React 18 + Vite, shadcn/ui, Tailwind CSS, Zustand, TanStack Query, Recharts |
| **Observability** | Prometheus metrics, structured audit logs, decision cards, Sentry-ready |

---

## 📸 Demo Preview

### Student Dashboard
![Student Dashboard](docs/assets/student-dashboard.png)

### Faculty Copilot
![Faculty Copilot](docs/assets/faculty-copilot.png)

### Placement Analytics
![Placement Analytics](docs/assets/placement-analytics.png)

### Agent Trace Panel (Showcase)
![Agent Trace](docs/assets/agent-trace.png)

---

## 🚀 Quickstart (Docker - Recommended)

### Prerequisites
- Docker Desktop / Docker Engine + Docker Compose
- 8GB+ RAM recommended

### One-Command Launch

```bash
# 1. Clone and configure
git clone <your-repo>
cd AI-CLG-AGENT
cp .env.example .env

# 2. Start all services (first run pulls images ~2-3 min)
docker compose up --build

# 3. Seed rich demo data (in another terminal)
docker compose exec backend python -m scripts.seed_demo
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | See demo accounts below |
| **API Docs (Swagger)** | http://localhost:8000/docs | — |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | — |
| **Neo4j Browser** | http://localhost:7474 | neo4j / beru-neo4j |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | — |
| **MLflow** | http://localhost:5000 | — |

---

## 🔑 Demo Accounts (Pre-Seeded)

| Role | Username | Password | Description |
|------|----------|----------|-------------|
| **Student (Strong)** | `STU2024001` | `student123` | 3.8 GPA, top performer |
| **Student (At-Risk)** | `STU2024005` | `student123` | 2.2 GPA, attendance issues |
| **Student (Critical)** | `STU2024009` | `student123` | 1.8 GPA, multiple failures |
| **Faculty** | `LEC001` | `lecturer123` | CS Department |
| **Placement Officer** | `placement` | `placement123` | Full placement access |
| **Admin** | `admin` | `admin123` | System administration |

> **Quick Demo Flow**: Login as `STU2024001` → Dashboard → Insights → Exam Prep → Mock Interview → Resume ATS → Agent Trace (admin/lecturer)

---

## 🎬 5-Minute Demo Script

### 1. Student Experience (2 min)
```
Login: STU2024001 / student123
├── Dashboard → Success Score (85), Low Risk
├── Courses table with predictions
├── "What should I do today?" → Personalized plan
├── Insights → Digital Twin, Progress trends
├── Exam Prep → CS301 practice quiz (5 Qs)
├── Mock Interview → "Software Engineer" role
├── Resume ATS → Paste resume, get score + suggestions
└── Project Mentor → "Final Year Capstone" guidance
```

### 2. Faculty Experience (1.5 min)
```
Login: LEC001 / lecturer123
├── Dashboard → At-risk students (STU2024005, STU2024009)
├── Course Health → CS301 attendance 68% ⚠️
├── Copilot → Generate Question Paper for CS301
├── Copilot → Lesson Plan: "Dynamic Programming" (50 min)
├── Similarity Check → Paste 2 submissions, detect plagiarism
└── Intervention → Create plan for STU2024005 in CS301
```

### 3. Placement Experience (1 min)
```
Login: placement / placement123
├── Dashboard → 3 active drives, 47 eligible students
├── JD Analyzer → Paste job description, extract skills
├── Matching → "ML Engineer" JD → Top 10 candidates
├── Analytics → Salary trends, Skill demand, Funnel
└── Drive → TechCorp Drive → View pipeline
```

### 4. Agent Trace Showcase (0.5 min)
```
Login: admin / admin123 (or LEC001)
├── Navigate to "Agent Trace" in sidebar
├── Query: "Which students are at risk in CS301?"
├── Watch: Memory → Router → Planner → Success Agent → Reflect → Terminal
├── Expand nodes to see metadata (intent, confidence, citations)
└── View final response with decision card ID
```

---

## 🛠️ Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux/Mac
pip install -r requirements.txt
# For ML: pip install -r requirements-ml.txt
uvicorn app.main:app --reload
```

- Runs on `http://localhost:8000`
- SQLite by default (`beru.db`) — no Postgres needed for dev
- Set `DATABASE_URL` in `.env` for PostgreSQL

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Runs on `http://localhost:5173`
- Vite proxies `/api` → `http://localhost:8000`

### Run Tests

```bash
cd backend
pytest -x -q              # Fast subset
pytest --cov=app          # With coverage
```

### Generate Synthetic Data

```bash
cd backend
python -m synthetic.cli --students 500 --courses 40 --seed 42 --out ../data
```

---

## 📁 Project Structure

```
AI-CLG-AGENT/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph supervisor + 4 specialists
│   │   ├── api/routes/       # REST endpoints (auth, students, faculty, placement, agents, admin)
│   │   ├── core/             # Security, audit, exceptions, safety
│   │   ├── ml/               # Features, training, prediction, optimization
│   │   ├── models/           # SQLAlchemy entities
│   │   ├── schemas/          # Pydantic contracts
│   │   ├── services/         # Domain services (RAG, LLM, graph, ML, notifications)
│   │   └── workers/          # Celery tasks
│   ├── scripts/
│   │   └── seed_demo.py      # 🌟 Rich demo data seeder
│   ├── synthetic/            # Deterministic data generator
│   ├── finetuning/           # LoRA/QLoRA training scripts
│   └── tests/                # 20+ test modules
├── frontend/
│   ├── src/
│   │   ├── modules/
│   │   │   ├── student/      # Student dashboard, tools, insights
│   │   │   ├── faculty/      # Faculty copilot, tools, reports
│   │   │   ├── placement/    # Drives, matching, analytics
│   │   │   ├── admin/        # Admin center, analytics
│   │   │   ├── common/       # Chat, analytics, 🌟 Agent Trace Panel
│   │   │   └── shared/       # 🌟 AgentTracePanel.tsx
│   │   └── core/             # Layout, auth, API client, UI components
├── data/                     # Curriculum corpus (229 chunks)
├── docs/
│   └── architecture.md       # 🌟 Full architecture with Mermaid diagrams
└── docker-compose.yml        # Full stack orchestration
```

---

## ⚙️ Environment Variables

See `.env.example` for full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./beru.db` | PostgreSQL for production |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + cache |
| `NEO4J_URI` | `bolt://localhost:7687` | Knowledge graph |
| `QDRANT_URL` | `http://localhost:6333` | Vector store |
| `GROQ_API_KEY` | *empty* | Cloud LLM (primary) |
| `GEMINI_API_KEY` | *empty* | Cloud LLM (secondary) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local LLM fallback |
| `LLM_PROVIDER_ORDER` | `groq,gemini,ollama` | Fallback chain |
| `JWT_SECRET` | `dev-secret-change-me` | **Change in production!** |
| `DEFAULT_ADMIN_PASSWORD` | `admin123` | **Change in production!** |

---

## 🔄 LLM Fallback Behavior

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM PROVIDER CHAIN                        │
├─────────────────────────────────────────────────────────────┤
│  1. Groq (Llama 3.3 70B)  ──fail──▶  2. Gemini (2.0 Flash)  │
│                                                        │       │
│                                                        ▼       │
│                                              3. Ollama (local) │
│                                                        │       │
│                                                        ▼       │
│                                              Deterministic     │
│                                              Rule-Based Fallback│
└─────────────────────────────────────────────────────────────┘
```

- **No API keys?** System works offline with rule-based responses
- **Ollama running?** Real local inference (llama3.2:3b default)
- **All providers fail?** Graceful degradation logged in audit trail

---

## 📚 Curriculum RAG

The in-process curriculum RAG (`backend/app/services/curriculum_rag.py`) provides:
- **Anna University AI&DS Regulations 2021** — 229 pre-chunked documents
- **Course Catalog** — 241 courses with prerequisites
- **Fallback Logic** — Activated when main RAG returns no evidence or LLM refuses
- **Citations** — Page-level references rendered as `[1] Title (p.42)`

Disable with: `CURRICULUM_RAG_ENABLED=false`

---

## 📊 Architecture Documentation

📖 **[Full Architecture Guide](docs/architecture.md)** — Includes:
- System overview & high-level diagrams
- Backend module structure
- Request flows (REST + Agent chat)
- LangGraph supervisor state machine
- RAG pipeline with provider fallback
- Database ER diagram
- Student success score computation
- Placement intelligence flow
- ML training/serving pipeline
- Security architecture
- Docker deployment topology
- Design decisions & future extensibility

---

## ✅ Verification Checklist

Before demo/submission, verify:

- [ ] `docker compose up --build` starts without errors
- [ ] `docker compose exec backend python -m scripts.seed_demo` completes
- [ ] Frontend loads at `http://localhost:5173`
- [ ] All 6 demo accounts can login
- [ ] Student dashboard shows success score, courses, predictions
- [ ] Faculty dashboard shows at-risk students, course health
- [ ] Placement dashboard shows drives, matching, analytics
- [ ] Agent Trace panel (`/agent-trace`) animates execution steps
- [ ] API docs accessible at `http://localhost:8000/docs`
- [ ] `pytest backend/tests -x -q` passes

---

## 🎓 Final Year Project Submission

### What This Demonstrates

| Competency | Evidence |
|------------|----------|
| **Full-Stack Development** | FastAPI + React, Docker, multi-service orchestration |
| **AI/ML Engineering** | LangGraph agents, RAG, XGBoost, MLflow, SHAP |
| **Database Design** | PostgreSQL + Neo4j + Qdrant + Redis polyglot persistence |
| **System Architecture** | Clean separation, domain-driven design, observability |
| **Software Engineering** | Testing, CI-ready, configuration management, documentation |
| **Domain Knowledge** | Academic operations, placement workflows, curriculum modeling |

### Talking Points for Viva

1. **"I built a multi-agent system with LangGraph"** — Show Agent Trace panel
2. **"Hybrid RAG with curriculum-specific fallback"** — Demo chat with citations
3. **"Graph database for prerequisite dependencies"** — Neo4j traversal in prereqs service
4. **"Production ML pipeline with MLflow"** — Training → Registry → Serving → Monitoring
5. **"Role-based access with audit trails"** — Hash-chained audit logs + decision cards
6. **"Real-time analytics for student success"** — Success score formula, risk bands, drivers

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **LangGraph** for agent orchestration framework
- **Groq** for fast LLM inference
- **Ollama** for local model hosting
- **Anna University** for curriculum reference data
- **shadcn/ui** for beautiful accessible components

---

*Built with ❤️ as a Final Year Project — Beru Campus AI Team*