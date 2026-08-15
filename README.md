# Beru Campus AI — Autonomous Multi-Agent University Operating System

> "An AI workforce that autonomously manages academic operations, predicts student success, and optimizes campus resources through collaborative AI agents."

## Free Stack

| Concern | Tool |
|---|---|
| Agent reasoning | Groq (Llama 3.3 70B / 3.1 8B) or Gemini Flash; fallback: Ollama (Llama 3.1 8B / Phi-3) |
| Embeddings | BAAI/bge-small-en-v1.5 (local); reranker bge-reranker-base |
| Orchestration | LangGraph |
| Backend | FastAPI, Celery + Redis, python-jose, passlib (bcrypt) |
| Databases | PostgreSQL, Neo4j CE, Qdrant (fallback ChromaDB), Redis |
| College knowledge base | In-process Curriculum RAG (Anna Univ AIDS Reg 2021, 229 chunks, ChromaDB collection) + Ollama |
| ML | scikit-learn, XGBoost, LightGBM, SHAP, LIME, OR-Tools, MLflow |
| Frontend | React + Vite, shadcn/ui, Tailwind CSS, Zustand/React Query, Recharts |
| DevOps | Docker Compose, GitHub Actions, Prometheus + Grafana, Sentry |

## Documentation

- `docs/PHASE1_Requirement_Analysis.md` — problem statement, scope, FRs/NFRs, stakeholders, use cases, user stories, modules
- `docs/PHASE2_System_Design.md` — architecture diagrams (Mermaid): HLA, LLA, components, deployment, sequences, classes, ER, DFD

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up -d postgres redis neo4j qdrant
docker compose up backend worker frontend
```

- Frontend: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- Default admin (created on first boot): `admin` / `admin123`

## Quickstart (Local dev)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt  # core; ML extras: pip install -r requirements-ml.txt
uvicorn app.main:app --reload
```

Backend runs standalone with SQLite (`beru.db`) — no Postgres required for the scaffold. Set `DATABASE_URL` to Postgres for full mode.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8000`.

### College curriculum RAG (knowledge base)

The college curriculum knowledge base (course units, syllabi, credits) is an **in-process service** inside the backend (`backend/app/services/curriculum_rag.py`), reading the Anna University AIDS Reg 2021 corpus from `data/` (229 chunks). It shares the same vector DB as the main KB but uses its own ChromaDB collection (`curriculum_documents`); the corpus is embedded at first boot (idempotent — restarts are fast). It is **integrated into the main RAG as a fallback**: when the main RAG retrieves no evidence or the main LLM refuses (e.g. "I could not find that information"), the backend delegates the question to the curriculum RAG and returns its cited, grounded answer.

No separate server or port is needed. Set `CURRICULUM_RAG_ENABLED=false` to disable the fallback.

When answering through the main assistant, curriculum answers arrive with `provider: "college-ai"` and citations rendered as `[i] <title> (p.<page>)`.

### Generate synthetic data

```bash
cd backend
python -m synthetic.cli --students 500 --courses 40 --seed 42 --out ../data
```

### Tests

```bash
cd backend
pytest
```

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── agents/        # LangGraph supervisor + 4 specialist agents
│   │   ├── api/routes/    # auth, agents, approvals, audit, predictions, synthetic
│   │   ├── core/          # security (JWT/bcrypt), hash-chained audit
│   │   ├── ml/            # features, train, predict, SHAP explain (lazy-loaded)
│   │   ├── models/        # SQLAlchemy entities (mirrors PHASE2 ER diagram)
│   │   ├── schemas/       # Pydantic contracts
│   │   ├── services/      # LLM gateway (Groq→Gemini→Ollama), RAG, curriculum RAG
│   │   └── workers/       # Celery app + tasks
│   ├── finetuning/        # LoRA/QLoRA training scripts + datasets (offline)
│   ├── synthetic/         # deterministic synthetic data generator (CLI + API)
│   └── tests/
├── frontend/              # React + Vite + shadcn/ui
├── data/                  # shared KB corpus + course index (229 chunks)
├── docs/                  # Phase 1 & Phase 2 documents
└── .github/workflows/     # CI
```

## Environment variables

See `.env.example`. Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./beru.db` | Postgres for full mode |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + cache |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | localhost / neo4j / password | Knowledge graph |
| `QDRANT_URL` | `http://localhost:6333` | Vector store |
| `VECTOR_STORE_BACKEND` | `qdrant` | `qdrant` or `chroma` |
| `GROQ_API_KEY` / `GEMINI_API_KEY` | empty | Cloud LLM providers |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local LLM fallback |
| `LLM_PROVIDER_ORDER` | `groq,gemini,ollama` | Fallback chain order |
| `COLLEGE_AI_URL` / `COLLEGE_AI_TIMEOUT_SECONDS` | removed | Former separate service — curriculum RAG is now in-process |
| `CURRICULUM_RAG_ENABLED` | `true` | Toggle the in-process curriculum RAG fallback |
| `CURRICULUM_RAG_JSONL` | `../data/anna_university_aids_reg2021_rag.jsonl` | Curriculum corpus (229 chunks) |
| `CURRICULUM_COLLECTION` | `curriculum_documents` | ChromaDB/Qdrant collection for the curriculum corpus |
| `CURRICULUM_SIMILARITY_THRESHOLD` | `0.35` | Min score for curriculum evidence |
| `JWT_SECRET` | dev-secret | Token signing |
| `DEFAULT_ADMIN_USER` / `DEFAULT_ADMIN_PASSWORD` | admin / admin123 | Seeded admin on first boot |

## LLM fallback behavior

No keys configured? The LLM Gateway degrades gracefully to a deterministic rule-based responder so every endpoint still works offline (documented in the audit trail as `provider=local-fallback`). With Ollama running locally, real local inference is used.

## Curriculum RAG fallback behavior

Independent of the LLM provider chain, the RAG service consults the in-process curriculum RAG (`backend/app/services/curriculum_rag.py`) when either of these holds:

1. **No evidence retrieved** — the main KB (`data/anna_university_aids_reg2021_rag.jsonl`) returns zero chunks above the similarity threshold.
2. **Main LLM refuses** — the answer matches refusal markers like `"could not find"`, `"unavailable"`, `"does not contain"`, etc.

The curriculum grounding engine answers strictly from its own ChromaDB corpus (229 chunks) and returns page-level citations; if it cannot ground an answer either, it replies with the exact refusal `"I could not find that information in the college knowledge base."` with `grounded: false` and no sources. Set `CURRICULUM_RAG_ENABLED=false` to disable this integration.
