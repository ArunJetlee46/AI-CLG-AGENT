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

## What's in the box

The assistant is a LangGraph supervisor with specialist agents (academic, success, resources, placement, attendance, exam, advising), all orchestrated in a single request pipeline. Recent capability themes:

| Theme | What it added |
|---|---|
| **A. Personalization** | Agent responses are personalized per student (risk, GPA, attendance, placement readiness) using a 4-stage reasoning loop — router, planner, reflect (critic off by default, `AGENT_LLM_REASONING_STAGES`). |
| **B. Persistent memory** | Every conversation is saved to `conversations` / `conversation_messages` (SQLite or Postgres) with per-actor pruning, so a student's history survives restarts and flows back into chat. |
| **C. Security hardening** | Refresh tokens with `jti` rotation + reuse detection (a replayed token revokes the whole chain, `401 token_reuse_detected`), `POST /auth/logout`, SlowAPI rate limits on login and chat, CORS policy from settings. |
| **D. Groq streaming** | `POST /agents/chat` with `{"stream": true}` returns an SSE stream (`chunk` / `done` / `error` events) with Groq as the primary streaming provider (Gemini/Ollama/local fallback emit whole-text). The web chat renders tokens live. |
| **E. Database → RAG backfill** | Live DB rows (courses, lecturers, rooms, companies, drives, resources, announcements, research, industry partners, aggregate student stats) are ingested into the vector store + keyword index and persisted to `data/database_rag.jsonl` so restarts rebuild instantly. Runs at boot and on demand via `POST /admin/rag-backfill`. Student PII never enters the corpus — only aggregate numbers. |
| **F. Final hardening + docs** | Web SSE consumption with session-refresh retry, dead-code removal, README/docs polish. |

All six themes are committed and pushed to `main`. The full backend suite (`pytest`) is green, and the frontend passes `tsc --noEmit` + vitest.

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

Streaming chat example:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"23AD001","password":"student123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -N -X POST http://localhost:8000/api/v1/agents/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"what are the tuition fees","stream":true}'
# -> data: {"type":"chunk","content":"..."} ... data: {"type":"done","intent":"academic",...}
```

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
│   │   ├── agents/        # LangGraph supervisor + specialist agents, memory, state
│   │   ├── api/routes/    # auth, agents (SSE streaming), approvals, audit, admin
│   │   ├── core/          # security (JWT/bcrypt + refresh rotation), rate limiting, audit
│   │   ├── ml/            # features, train, predict, SHAP explain (lazy-loaded)
│   │   ├── models/        # SQLAlchemy entities (incl. RefreshToken, conversations)
│   │   ├── schemas/       # Pydantic contracts
│   │   ├── services/      # LLM gateway (Groq→Gemini→Ollama), RAG, DB→RAG backfill
│   │   └── workers/       # Celery app + tasks
│   ├── finetuning/        # LoRA/QLoRA training scripts + datasets (offline)
│   ├── synthetic/         # deterministic synthetic data generator (CLI + API)
│   └── tests/
├── frontend/              # React + Vite + shadcn/ui (SSE live-rendered chat)
├── data/                  # shared KB corpus, course index, database_rag.jsonl (gitignored)
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
| `LLM_PROVIDER_ORDER` | `groq,ollama,gemini` | Fallback chain order |
| `AGENT_LLM_REASONING_STAGES` | `router,planner,reflect` | Reasoning stages run by the supervisor |
| `EMBEDDING_BACKEND` | `onnx` | Local embedding backend (`onnx` or `local`) |
| `DB_RAG_BACKFILL_ENABLED` | `true` | Boot-time DB → RAG backfill + `database_rag.jsonl` write |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins; production refuses `*` |
| `LOGIN_RATE_LIMIT` / `CHAT_RATE_LIMIT` | `10/minute` / `60/minute` | SlowAPI limits on `/auth/login` and `/agents/chat` |
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
