# PHASE 2 — System Design

## Beru Campus AI — Autonomous Multi-Agent University Operating System

| Field | Value |
|---|---|
| Project | Beru Campus AI |
| Phase | Phase 2 — System Design |
| Document Version | 1.0 |
| Status | Draft |
| Last Updated | 2026-08-11 |
| Prerequisite | docs/PHASE1_Requirement_Analysis.md |

**Scope of this document:** High-Level Architecture, Low-Level Architecture, Component Diagram, Deployment Diagram, Sequence Diagrams, Class Diagram, ER Diagram, and Data Flow Diagram — all in Mermaid, explained component by component, mapped to the approved free stack (Groq/Gemini + Ollama fallback, Qdrant/Chroma retrieval, LangGraph, FastAPI, PostgreSQL, Neo4j, Redis, Celery, Docker Compose, Prometheus/Grafana, Sentry).

---

## 1. Design Goals & Principles

| # | Principle | Consequence in design |
|---|---|---|
| P1 | **Zero-cost by default** | Every heavy service has a local fallback (Ollama for LLM, ChromaDB for Qdrant, SQLite fallback only for dev if needed). |
| P2 | **Graceful degradation** | The LLM Gateway implements a deterministic fallback chain: Groq → Gemini → Ollama. If the network dies, the system still answers locally. |
| P3 | **Human-in-the-loop for high impact** | Every mutating/high-stakes action passes an approval gate; the graph pauses and resumes. |
| P4 | **Everything is audited** | A single Audit Interceptor wraps all agent actions, LLM calls, predictions, and approvals (hash-chained, append-only). |
| P5 | **Agents are stateless; state lives in the graph** | LangGraph holds shared `AgentState`; agents are pure functions over that state. |
| P6 | **Asynchronous by default** | Long tasks (data generation, training, timetabling, notifications) run on Celery workers, never in the HTTP path. |
| P7 | **Single source of truth + read models** | PostgreSQL is the transactional source of truth; Neo4j (graph), Qdrant (vectors), Redis (cache/queue) are derived read-optimized stores. |

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph Client
        F["React SPA<br/>(Vercel / Netlify free tier)"]
    end

    subgraph Backend["Backend (Render / Fly.io free tier)"]
        API["FastAPI Gateway<br/>JWT + RBAC (python-jose, bcrypt)"]
        ORC["LangGraph Supervisor<br/>(shared AgentState)"]
        A1["Academic Ops Agent<br/>(RAG + registration)"]
        A2["Student Success Agent<br/>(predict + explain)"]
        A3["Resource Optimizer Agent<br/>(OR-Tools)"]
        A4["Knowledge Agent<br/>(NL to Cypher)"]
        AUD["Audit Trail Agent<br/>(hash-chained log)"]
        WK["Celery Workers<br/>+ Beat (scheduled)"]
    end

    subgraph Data["Data Layer (self-hosted, Docker)"]
        PG[("PostgreSQL<br/>source of truth")]
        NEO[("Neo4j CE<br/>knowledge graph")]
        QD[("Qdrant / ChromaDB<br/>vector store")]
        RD[("Redis<br/>cache + broker")]
        MLF[("MLflow<br/>experiments + registry")]
    end

    subgraph LLM["LLM Providers"]
        GQ["Groq Cloud<br/>Llama 3.3 70B / 3.1 8B"]
        GM["Google Gemini Flash"]
        OL["Ollama (local)<br/>Llama 3.1 8B / Phi-3"]
    end

    subgraph Obs["Observability"]
        PRO["Prometheus"]
        GRAF["Grafana"]
        SEN["Sentry"]
    end

    F -->|"HTTPS REST / SSE"| API
    API --> ORC
    ORC --> A1
    ORC --> A2
    ORC --> A3
    ORC --> A4
    A1 --> AUD
    A2 --> AUD
    A3 --> AUD
    A4 --> AUD
    A1 --> QD
    A4 --> NEO
    A1 --> PG
    A2 --> PG
    A3 --> PG
    ORC --> RD
    API --> WK
    WK --> PG
    WK --> NEO
    WK --> QD
    API --> MLF
    WK --> MLF
    A1 -->|"LLM calls via gateway"| LLM
    A2 -->|"LLM calls via gateway"| LLM
    A3 -->|"LLM calls via gateway"| LLM
    A4 -->|"LLM calls via gateway"| LLM
    API --> PRO
    WK --> PRO
    API --> SEN
    PRO --> GRAF
```

### Component-by-component explanation (HLA)

| Component | Role in the system | Free-stack mapping |
|---|---|---|
| **React SPA** | The only user surface. Three role views (Student Portal, Lecturer Console, Admin Command Center) render from REST + Server-Sent Events. | React, Vite, shadcn/ui, Tailwind, Zustand, React Query, Recharts |
| **FastAPI Gateway** | Single entry point. Authenticates (JWT), enforces RBAC, validates Pydantic schemas, streams agent responses via SSE, and forwards long tasks to Celery. | FastAPI, python-jose, passlib/bcrypt |
| **LangGraph Supervisor** | Orchestrator. Receives an intent from the gateway, selects the specialist agent, threads a shared `AgentState` between agents, and manages approval gates. It is the only component that talks to all agents. | LangGraph |
| **Specialist Agents (A1–A4)** | Each encapsulates one domain: academic operations (registration/reports/RAG Q&A), student success (prediction + intervention drafting), resource optimization (timetabling), and knowledge-graph querying. All read/write the same stores but own different business rules. | LangGraph nodes, LangChain tools |
| **Audit Trail Agent** | Cross-cutting. Every agent emits audit events; this agent persists them append-only with hash chaining and assembles "Decision Cards". Never on a hot path; writes are async. | PostgreSQL (append-only tables), FastAPI events |
| **Celery Workers + Beat** | Execute long-running jobs (synthetic data generation, model training, timetable solving, scheduled re-scoring of students, notifications) off the HTTP path. | Celery, Redis broker |
| **PostgreSQL** | Transactional source of truth: users, enrollments, grades, attendance, audit logs, decisions, model metadata. | PostgreSQL 16 (self-hosted) |
| **Neo4j** | Knowledge graph: entities (Student, Course, Lecturer, Room, Department) and relationships (enrolls, teaches, prerequisite, scheduled_in). Powers cross-domain questions. | Neo4j Community Edition |
| **Qdrant / ChromaDB** | Vector index over institutional documents and (optionally) course material embeddings. Qdrant is primary; ChromaDB is the embedded fallback when Qdrant is down. | Qdrant (Docker) / ChromaDB (embedded) |
| **Redis** | Celery broker + result backend, JWT blacklist/rate-limits, and pub/sub for live dashboard events. | Redis 7 |
| **MLflow** | Tracks experiments, registers models, stores SHAP baselines. | MLflow (self-hosted) |
| **LLM Providers** | Reasoning engines. Order: Groq (fast, free quota) → Gemini Flash (second quota pool) → Ollama (local, always available). | Groq, Gemini, Ollama |
| **Prometheus / Grafana / Sentry** | Pull metrics from API + workers; dashboards; error tracking. | Prometheus, Grafana, Sentry free tier |

---

## 3. Low-Level Architecture

```mermaid
flowchart TB
    subgraph L1["Layer 1 — Presentation"]
        P1["Student Portal"]
        P2["Lecturer Console"]
        P3["Admin Command Center"]
    end

    subgraph L2["Layer 2 — API & Auth (FastAPI)"]
        R1["REST routes /api/v1/*"]
        R2["AuthService: login/refresh, RBAC dependency"]
        R3["SSE event stream"]
        R4["Pydantic request/response contracts"]
    end

    subgraph L3["Layer 3 — Orchestration (LangGraph)"]
        O1["SupervisorGraph: intent router"]
        O2["AgentState: shared message + tool memory"]
        O3["HITL gate: checkpoint & resume"]
    end

    subgraph L4["Layer 4 — Agents"]
        AG1["AcademicOpsAgent"]
        AG2["StudentSuccessAgent"]
        AG3["ResourceOptimizerAgent"]
        AG4["KnowledgeAgent"]
    end

    subgraph L5["Layer 5 — Domain Services"]
        S1["LLMGateway<br/>(Groq → Gemini → Ollama)"]
        S2["RAGService<br/>(embed → retrieve → rerank → answer)"]
        S3["MLEngine (XGBoost/LightGBM)"]
        S4["Explainer (SHAP/LIME)"]
        S5["OptimizerService (OR-Tools)"]
        S6["GraphService (Cypher)"]
        S7["SyntheticDataService"]
        S8["AuditService"]
    end

    subgraph L6["Layer 6 — Persistence & Infra"]
        D1[("PostgreSQL")]
        D2[("Neo4j")]
        D3[("Qdrant")]
        D4[("ChromaDB fallback")]
        D5[("Redis")]
        D6[("MLflow artifacts")]
    end

    subgraph L7["Layer 7 — Async & Cross-Cutting"]
        X1["Celery Worker pool"]
        X2["Celery Beat scheduler"]
        X3["Prometheus exporter"]
        X4["Sentry SDK"]
    end

    L1 --> L2
    R1 --> O1
    R2 --> R1
    R3 --> R1
    O1 --> O2
    O1 --> AG1
    O1 --> AG2
    O1 --> AG3
    O1 --> AG4
    O3 --> O1
    AG1 --> S1
    AG1 --> S2
    AG2 --> S3
    AG2 --> S4
    AG2 --> S1
    AG3 --> S5
    AG4 --> S6
    AG4 --> S1
    AG1 --> S8
    AG2 --> S8
    AG3 --> S8
    AG4 --> S8
    S2 --> D3
    S2 --> D4
    S6 --> D2
    S3 --> D6
    S5 --> D1
    S7 --> D1
    S7 --> D2
    S7 --> D3
    S8 --> D1
    O1 --> D5
    R1 --> X1
    X1 --> S7
    X1 --> S3
    X1 --> S5
    X2 --> X1
    L2 --> X3
    L2 --> X4
```

### Layer-by-layer explanation

| Layer | Contents | Explanation |
|---|---|---|
| **L1 Presentation** | 3 role-based React views | Views differ only in data they may request; the backend enforces RBAC, so the SPA never trusts the client. |
| **L2 API & Auth** | REST + SSE + contracts | Every route has a Pydantic contract. `AuthService` issues JWTs and the RBAC dependency rejects unauthorized calls before any agent runs. Long-running agent turns stream tokens over SSE. |
| **L3 Orchestration** | Supervisor graph + state | The `SupervisorGraph` is a LangGraph state machine: nodes are the four agents, edges are intent decisions. `AgentState` carries the conversation, tool results, and gate flags. When an agent requests approval, the graph **checkpoints** (LangGraph persistence) and sleeps until an admin decision resumes it. |
| **L4 Agents** | 4 specialists | Each agent is a graph node with its own tool set. No agent calls another agent directly — all routing goes through the supervisor, keeping the system a strict hierarchy (easier to audit and test). |
| **L5 Domain Services** | Reusable, agent-agnostic services | `LLMGateway` (fallback chain), `RAGService` (retrieval pipeline), `MLEngine` + `Explainer` (prediction + SHAP/LIME), `OptimizerService` (OR-Tools), `GraphService` (Cypher), `SyntheticDataService`, `AuditService`. Services are shared between agents and Celery tasks — this is what keeps code DRY. |
| **L6 Persistence** | 4 DBs + artifacts | Postgres = truth, Neo4j = relationships, Qdrant = embeddings (Chroma fallback), Redis = queue/cache/events, MLflow = experiment artifacts. |
| **L7 Async & Cross-Cutting** | Celery + observability | Celery workers run all heavy tasks. Prometheus exports `/metrics`; Sentry captures exceptions. |

---

## 4. Component Diagram

```mermaid
flowchart LR
    subgraph UI["Presentation"]
        SPA["React SPA"]
    end

    subgraph BFF["Backend Services"]
        AUTH["Auth Service"]
        API["REST/SSE API"]
        ORCH["Supervisor Graph"]
        AO["Academic Ops Agent"]
        SA["Student Success Agent"]
        RO["Resource Optimizer Agent"]
        KA["Knowledge Agent"]
        AUDIT["Audit Service"]
        CELERY["Celery Tasks"]
    end

    subgraph LIB["Shared Libraries / Interfaces"]
        LLMG["LLM Gateway Interface"]
        RAGS["RAG Pipeline"]
        VECS["VectorStore Interface"]
        MLE["ML Service"]
        ORT["OR-Tools Wrapper"]
        GQS["Neo4j Client"]
    end

    subgraph EXT["External Providers"]
        GROQ["Groq API"]
        GEM["Gemini API"]
        OLLAMA["Ollama local"]
        MLFLOW["MLflow Server"]
    end

    subgraph INFRA["Infrastructure"]
        PG[("Postgres")]
        NEO[("Neo4j")]
        QDR[("Qdrant")]
        CHR[("ChromaDB")]
        REDIS[("Redis")]
        PROM["Prometheus"]
        GRAFANA["Grafana"]
        SENTRY["Sentry"]
    end

    SPA -->|"HTTPS"| API
    SPA -->|"login"| AUTH
    API --> AUTH
    API --> ORCH
    ORCH --> AO
    ORCH --> SA
    ORCH --> RO
    ORCH --> KA
    AO --> LLMG
    SA --> LLMG
    KA --> LLMG
    AO --> RAGS
    RAGS --> VECS
    SA --> MLE
    RO --> ORT
    KA --> GQS
    LLMG --> GROQ
    LLMG --> GEM
    LLMG --> OLLAMA
    VECS --> QDR
    VECS --> CHR
    GQS --> NEO
    API --> PG
    AO --> PG
    SA --> PG
    RO --> PG
    AUDIT --> PG
    CELERY --> PG
    CELERY --> QDR
    CELERY --> NEO
    CELERY --> MLE
    CELERY --> MLFLOW
    API --> REDIS
    CELERY --> REDIS
    API --> PROM
    CELERY --> PROM
    API --> SENTRY
    PROM --> GRAFANA
```

### Interfaces (contracts between components)

| Interface | Direction | Transport | Payload example |
|---|---|---|---|
| `POST /api/v1/auth/login` | SPA → Auth | REST | `{username, password}` → `{access_token, refresh_token}` |
| `POST /api/v1/agents/chat` | SPA → API | REST + SSE | `{message}` → streamed tokens + final `DecisionCard` |
| `POST /api/v1/approvals/{id}` | SPA → API | REST | `{decision: approve/reject, comment}` |
| `GET /api/v1/audit?filters` | SPA → API | REST | filter params → paginated audit rows |
| `LLMGateway.complete()` | Agent → LLM GW | in-process | `(messages, tools)` → `(response, provider_used, cost, latency)` |
| `VectorStore.search()` | RAG → Qdrant/Chroma | gRPC/REST or embedded | `(query_embedding, top_k)` → scored docs |
| `GraphService.query()` | Agent → Neo4j | Bolt | `(cypher, params)` → records |
| `broker.publish()` | API/Worker → Redis | RESP | JSON job payload |
| `/metrics` | API/Worker → Prometheus | HTTP scrape | Prometheus text format |

---

## 5. LLM Fallback & RAG Retrieval Paths

### 5.1 LLM Gateway fallback chain

```mermaid
flowchart LR
    CALL(["LLM request from agent"])
    CALL --> GQ["Groq API<br/>Llama 3.3 70B"]
    GQ -->|"ok"| OUT["return response<br/>+ provider metadata"]
    GQ -->|"quota / 429 / 5xx / timeout"| GM["Gemini Flash"]
    GM -->|"ok"| OUT
    GM -->|"quota / error / offline"| OL["Ollama local<br/>Llama 3.1 8B / Phi-3"]
    OL -->|"ok"| OUT
    OL -->|"model not found / busy"| FAIL["degrade: rule-based fallback answer<br/>+ audit warning"]
    GQ -.->|"track calls/quota"| RD[("Redis counters")]
    GM -.->|"track calls/quota"| RD
    OUT --> AUD[("Audit: provider, latency, tokens, model")]
```

**Fallback rules:** the gateway tries providers in order (Groq → Gemini → Ollama). It only falls through on hard failures (HTTP ≥ 400, quota, timeout > N s). A **circuit breaker** trips a provider for 60 s after 3 consecutive failures, skipping it immediately. Usage counters in Redis keep the system under free-tier quotas (e.g., "stop using Gemini after X requests/hour"). Every call is audited with `provider_used`, latency, and token counts so the FYP report can show cost and resilience data.

### 5.2 RAG retrieval flow (Qdrant primary → Chroma fallback)

```mermaid
flowchart LR
    Q["user question"] --> EMB["Embedder<br/>BAAI/bge-small-en-v1.5<br/>(local, ONNX/SentenceTransformers)"]
    EMB --> VEC["query vector (384-dim)"]
    VEC --> QD["Qdrant<br/>hnsw search, top-k=20"]
    QD -->|"qdrant healthy"| CAND["20 candidate chunks"]
    QD -.->|"qdrant down"| CH["ChromaDB fallback<br/>(same embedding, same top-k)"]
    CH --> CAND
    CAND --> RR["Reranker<br/>bge-reranker-base (local)"]
    RR --> TOP["top-4 chunks, re-scored"]
    TOP --> LLM2["LLM Gateway: answer with citations"]
    LLM2 --> ANS["final answer + [source] refs"]
    ANS --> AUD2[("Audit: sources, scores, provider")]
```

**Retrieval explanation:** the query is embedded locally (never sent to an API, so retrieval works offline). Qdrant returns 20 candidate chunks (recall-biased), the local reranker re-scores and keeps 4 (precision-biased), and the LLM is prompted with only those 4 chunks plus an instruction to cite them. The answer surface includes source IDs so the UI can link back to the original document. If Qdrant is unreachable, the same `VectorStore` interface switches to ChromaDB (embedded, zero extra infra) — this satisfies the "retrieval still works on a plane" requirement.

---

## 6. Sequence Diagrams

### 6.1 Student Q&A (RAG) with audit

```mermaid
sequenceDiagram
    autonumber
    participant U as Student (SPA)
    participant API as FastAPI Gateway
    participant ORC as Supervisor Graph
    participant A1 as Academic Ops Agent
    participant RAG as RAG Service
    participant LLM as LLM Gateway
    participant PG as PostgreSQL
    participant AUD as Audit Service
    participant RED as Redis (cache)

    U->>API: POST /api/v1/agents/chat {question}
    API->>ORC: route intent (supervisor)
    ORC->>A1: run(question)
    A1->>RED: cache lookup (question hash)
    alt cache miss
        A1->>RAG: retrieve(question)
        RAG-->>A1: top-4 cited chunks
        A1->>LLM: complete(messages + chunks)
        LLM->>LLM: try Groq -> Gemini -> Ollama
        LLM-->>A1: answer + provider metadata
    end
    A1->>AUD: emit event (action, prompt hash, answer, provider)
    AUD->>PG: INSERT audit_log + decision_card
    A1-->>ORC: final state
    ORC-->>API: answer + citations
    API-->>U: 200 (streamed), decision card ref
```

### 6.2 Registration with Human-in-the-Loop gate

```mermaid
sequenceDiagram
    autonumber
    participant S as Student (SPA)
    participant API as FastAPI Gateway
    participant ORC as Supervisor Graph
    participant A1 as Academic Ops Agent
    participant NEO as Neo4j
    participant PG as PostgreSQL
    participant AUD as Audit Service
    participant AD as Admin (SPA)

    S->>API: POST /agents/register {course_ids}
    API->>ORC: route intent
    ORC->>A1: run(registration)
    A1->>NEO: Cypher: prerequisites OK?
    A1->>PG: check capacity + timetable clash
    alt all checks pass
        A1-->>ORC: requires_approval = true
        ORC->>AUD: create approval request
        AUD->>PG: INSERT approval_request (pending)
        API-->>S: 202 Accepted: pending approval
        AD->>API: POST /approvals/{id} {approve}
        API->>ORC: resume checkpointed graph
        ORC->>A1: execute enrollment
        A1->>PG: INSERT enrollment
        A1->>AUD: Decision Card (inputs, rule, approver)
        AUD->>PG: INSERT decision_card
        API-->>S: 201 registered (SSE notify)
    else check fails
        A1-->>ORC: blocked + reasons
        ORC-->>API: 422 with resolution options
        API-->>S: alternatives suggested
    end
```

### 6.3 Scheduled risk prediction

```mermaid
sequenceDiagram
    autonumber
    participant BEAT as Celery Beat
    participant W as Celery Worker
    participant ML as MLEngine
    participant EX as SHAP Explainer
    participant PG as PostgreSQL
    participant AUD as Audit Service
    participant LEC as Lecturer (SPA)
    participant RED as Redis (pub/sub)

    BEAT->>W: task: predict_midterm()
    W->>PG: load feature rows (synthetic cohorts)
    W->>ML: score each student
    ML-->>W: risk probabilities
    W->>EX: explain top-N at-risk
    EX-->>W: SHAP force/lists
    W->>PG: INSERT predictions (with shap_json)
    W->>AUD: Decision Cards (model, version, features, explanation)
    AUD->>PG: INSERT decision_card
    W->>RED: publish "risk_update" event
    RED-->>LEC: live dashboard refresh (SSE)
```

---

## 7. Deployment Diagram

```mermaid
flowchart TB
    subgraph LAP["Developer Laptop / FYP Demo Machine"]
        BE["backend: FastAPI + LangGraph + Celery"]
        PG[("postgres:16")]
        RD[("redis:7")]
        NEO[("neo4j:5 CE")]
        QDR[("qdrant:latest")]
        MLF[("mlflow:2.x")]
        OLL["ollama: llama3.1-8b / phi3"]
        PRO["prometheus"]
        GRAF["grafana"]
    end

    subgraph WEB["Vercel / Netlify (free tier)"]
        SPA["React SPA (static build)"]
    end

    subgraph GROQN["Groq Cloud (free tier)"]
        GROQA["Llama 3.3 70B / 3.1 8B API"]
    end

    subgraph GMN["Google Cloud (free tier)"]
        GMA["Gemini Flash API"]
    end

    subgraph SENN["Sentry (free tier)"]
        SENA["Sentry ingest"]
    end

    SPA -->|"HTTPS / SSE"| BE
    BE -->|"HTTPS"| GROQA
    BE -->|"HTTPS"| GMA
    BE -->|"localhost:11434"| OLL
    BE -->|"bolt://neo4j:7687"| NEO
    BE -->|"postgres://postgres:5432"| PG
    BE -->|"redis://redis:6379"| RD
    BE -->|"qdrant:6333"| QDR
    BE -->|"mlflow:5000"| MLF
    BE -->|"HTTP"| SENA
    PRO --> BE
    GRAF --> PRO
```

### Deployment notes (component by component)

| Deployable | Host | Notes |
|---|---|---|
| **React SPA** | Vercel/Netlify free | Static build; talks to the backend URL from `VITE_API_URL` env. |
| **FastAPI + LangGraph + Celery** | Render free (web + worker services) or Docker on demo laptop | Same image; web service runs Uvicorn, worker service runs `celery -A app.workers.celery_app worker`. On Render the free web service sleeps after inactivity — acceptable for demo; the laptop stack is the primary defense environment. |
| **PostgreSQL, Redis, Neo4j, Qdrant, MLflow, Prometheus, Grafana, Ollama** | Local Docker Compose | Not hosted on free clouds — too heavy/costly; all run via `docker compose up` and are reachable by the backend on the compose network. |
| **Groq / Gemini APIs** | External clouds | Zero cost within free quotas; used only when online. |
| **Ollama** | Local laptop | The offline guarantee: answers, embeddings, and reranking all work with zero internet. |
| **Sentry** | Cloud free tier | Error capture; DSN optional (disabled if unset). |

---

## 8. Class Diagram (Core Backend)

```mermaid
classDiagram
    direction LR

    class User {
        +id: UUID
        +username: str
        +password_hash: str
        +role: Role
        +email: EmailStr
        +is_active: bool
        +verify_password(pw: str) bool
    }
    class Student {
        +student_id: str
        +year: int
        +program: str
        +gpa: float
    }
    class Lecturer {
        +staff_id: str
        +department: str
        +max_hours: int
    }
    class Admin {
        +permissions: list[str]
    }
    class Enrollment {
        +id: UUID
        +status: EnrollmentStatus
        +enrolled_at: datetime
    }
    class Course {
        +code: str
        +title: str
        +credits: int
        +capacity: int
        +prerequisites: list[Course]
    }
    class Result {
        +grade: str
        +marks: float
        +semester: str
    }
    class AttendanceRecord {
        +date: date
        +status: str
    }
    class AuditLog {
        +id: UUID
        +actor: str
        +action: str
        +entity_type: str
        +entity_id: UUID
        +timestamp: datetime
        +prev_hash: str
        +hash: str
        +payload: JSON
    }
    class DecisionCard {
        +id: UUID
        +decision_type: str
        +inputs: JSON
        +reasoning: str
        +model_version: str
        +shap_values: JSON
        +approver: str
        +approved_at: datetime
    }
    class Prediction {
        +student_id: UUID
        +course_id: UUID
        +probability: float
        +risk_level: str
        +shap_json: JSON
        +model_version: str
        +created_at: datetime
    }

    class BaseAgent {
        <<abstract>>
        +name: str
        +run(state: AgentState) AgentState
        +emit_audit(event: AuditEvent) void
    }
    class AcademicOpsAgent
    class StudentSuccessAgent
    class ResourceOptimizerAgent
    class KnowledgeAgent
    class SupervisorGraph {
        -state: AgentState
        +route(intent: str) BaseAgent
        +checkpoint() void
        +resume(gate_id: UUID) void
    }
    class AgentState {
        +messages: list[ChatMessage]
        +tool_results: dict
        +approval_flags: dict
    }

    class LLMGateway {
        -providers: list[LLMProvider]
        -circuit: dict[str, int]
        +complete(messages, tools) LLMResponse
        -_try_provider(provider) LLMResponse
    }
    class RAGService {
        +retrieve(query: str) list[Chunk]
        +answer(query: str) RAGAnswer
    }
    class VectorStore {
        <<interface>>
        +search(embedding, top_k) list[ScoredChunk]
    }
    class QdrantStore
    class ChromaStore
    class EmbeddingService {
        +embed(texts) list[Vector]
    }
    class RerankerService {
        +rerank(query, candidates, keep) list[Chunk]
    }
    class MLEngine {
        +load_model(version) Model
        +predict(features) float
    }
    class Explainer {
        +explain(model, instance) Explanation
    }
    class OptimizerService {
        +solve(courses, rooms, lecturers) Timetable
    }
    class GraphService {
        +query(cypher, params) Records
    }
    class AuditService {
        +record(event) AuditLog
        +decision_card(card) DecisionCard
        +export_csv(filters) bytes
    }
    class SyntheticDataGenerator {
        +generate(config: GenConfig) DatasetBundle
    }

    User <|-- Student
    User <|-- Lecturer
    User <|-- Admin
    Course "1" -- "0..*" Course : prerequisites
    Course "1" --> "0..*" Enrollment
    Student "1" --> "0..*" Enrollment
    Enrollment "1" --> "0..1" Result
    Student "1" --> "0..*" AttendanceRecord
    Student "1" --> "0..*" Prediction
    Course "1" --> "0..*" Prediction

    BaseAgent <|-- AcademicOpsAgent
    BaseAgent <|-- StudentSuccessAgent
    BaseAgent <|-- ResourceOptimizerAgent
    BaseAgent <|-- KnowledgeAgent
    SupervisorGraph --> BaseAgent
    SupervisorGraph *-- AgentState

    LLMGateway ..> AcademicOpsAgent : used by
    RAGService ..> AcademicOpsAgent
    VectorStore <|.. QdrantStore
    VectorStore <|.. ChromaStore
    RAGService --> VectorStore
    RAGService --> EmbeddingService
    RAGService --> RerankerService
    MLEngine ..> StudentSuccessAgent
    Explainer ..> StudentSuccessAgent
    OptimizerService ..> ResourceOptimizerAgent
    GraphService ..> KnowledgeAgent
    AuditService ..> BaseAgent
    SyntheticDataGenerator ..> AuditService

    AuditLog "1" --> "0..1" DecisionCard : produced_by
```

### Class-diagram notes

- **BaseAgent** is the contract every agent implements (`run(state) -> state`); `SupervisorGraph` only depends on `BaseAgent`, so adding a 5th agent later requires zero changes to the orchestrator (satisfies NFR extensibility).
- **AuditService** is referenced by every agent (the audit interceptor), guaranteeing 100% coverage of actions.
- **VectorStore** is an interface implemented by `QdrantStore` (primary) and `ChromaStore` (fallback) — this is the abstraction that makes the Qdrant/Chroma switch a one-line config change.
- **LLMGateway** hides provider logic; agents never import Groq/Gemini/Ollama SDKs directly.
- ER-style relationships (User/Student/Enrollment…) mirror the PostgreSQL schema in section 9.

---

## 9. ER Diagram (PostgreSQL Schema)

```mermaid
erDiagram
    users ||--o| students : "profile"
    users ||--o| lecturers : "profile"
    users ||--o| admins : "profile"
    users ||--o{ audit_logs : "performs"
    users ||--o{ approval_requests : "requests"

    courses ||--o{ enrollments : "enrolled in"
    students ||--o{ enrollments : "has"
    courses ||--o| courses : "prerequisite of"
    enrollments ||--o| results : "produce"
    courses ||--o{ results : "graded by"
    enrollments ||--o{ attendance : "recorded in"
    students ||--o{ attendance : "attends"
    students ||--o{ predictions : "scored by"
    courses ||--o{ predictions : "scored for"
    courses ||--o{ timetable_entries : "scheduled as"
    rooms ||--o{ timetable_entries : "allocated to"
    lecturers ||--o{ timetable_entries : "assigned to"
    audit_logs ||--o| decision_cards : "summarized by"
    models ||--o{ predictions : "version of"
    intervention_plans }o--|| predictions : "based on"
    students ||--o{ intervention_plans : "receives"

    users {
        uuid id PK
        string username UK
        string password_hash
        string role
        string email
        boolean is_active
        timestamp created_at
    }
    students {
        uuid id PK, FK
        string student_id UK
        int year
        string program
        numeric gpa
    }
    lecturers {
        uuid id PK, FK
        string staff_id UK
        string department
        int max_hours
    }
    admins {
        uuid id PK, FK
        jsonb permissions
    }
    courses {
        uuid id PK
        string code UK
        string title
        int credits
        int capacity
    }
    enrollments {
        uuid id PK
        uuid student_id FK
        uuid course_id FK
        string status
        timestamp enrolled_at
        uuid approved_by FK
    }
    results {
        uuid id PK
        uuid enrollment_id FK
        numeric marks
        string grade
        string semester
    }
    attendance {
        uuid id PK
        uuid enrollment_id FK
        date day
        string status
    }
    rooms {
        uuid id PK
        string room_no UK
        int capacity
        string type
    }
    timetable_entries {
        uuid id PK
        uuid course_id FK
        uuid room_id FK
        uuid lecturer_id FK
        string day
        time start_time
        time end_time
        string term
    }
    predictions {
        uuid id PK
        uuid student_id FK
        uuid course_id FK
        uuid model_id FK
        numeric probability
        string risk_level
        jsonb shap_values
        timestamp created_at
    }
    intervention_plans {
        uuid id PK
        uuid prediction_id FK
        text plan_text
        string status
        uuid notified_lecturer_id FK
    }
    audit_logs {
        uuid id PK
        uuid user_id FK
        string action
        string entity_type
        uuid entity_id
        jsonb payload
        string prev_hash
        string hash
        timestamp created_at
    }
    decision_cards {
        uuid id PK
        uuid audit_log_id FK
        string decision_type
        jsonb inputs
        text reasoning
        string model_version
        uuid approver_id FK
        timestamp decided_at
    }
    approval_requests {
        uuid id PK
        uuid user_id FK
        string intent
        jsonb payload
        string status
        timestamp created_at
        timestamp decided_at
    }
    models {
        uuid id PK
        string name
        string version
        string path
        jsonb metrics
        timestamp trained_at
    }
```

### ER explanation

| Entity | Purpose | Key notes |
|---|---|---|
| `users` + `students/lecturers/admins` | Auth + role profiles | Single-table `users` with polymorphic profiles (1:0..1). Simplest RBAC for an FYP; `role` field + profile FK. |
| `courses` | Catalog | Self-referencing FK `prerequisite_of` captures prerequisites in relational form (mirrored in Neo4j for traversal). |
| `enrollments` | Registration | `status` = pending/approved/rejected; `approved_by` records the HITL approver — this is how the audit chain is kept complete. |
| `results`, `attendance` | Academic history | Keyed by enrollment; feeds the ML feature set. |
| `rooms`, `timetable_entries` | Resource state | Solver output lands here; conflicts are impossible post-optimization but the solver validates before write. |
| `predictions`, `intervention_plans` | ML outputs | `shap_values` stored as JSON so every prediction is self-explanatory; `model_id` ties to `models` for reproducibility (MLflow version). |
| `audit_logs`, `decision_cards`, `approval_requests` | Governance | Append-only `audit_logs` with `prev_hash`/`hash` hash-chaining (tamper-evidence). `decision_cards` summarize *why*; `approval_requests` link the HITL gate. |
| `models` | ML registry mirror | Points at MLflow artifact paths; keeps the DB queryable without contacting MLflow. |

---

## 10. Data Flow Diagram

### 10.1 Context Diagram (DFD Level 0)

```mermaid
flowchart LR
    STU["Student"] -->|"questions, registrations,<br/>profile queries"| SYS["Beru Campus AI<br/>System"]
    LEC["Lecturer"] -->|"reports, risk alerts,<br/>timetable views"| SYS
    ADM["Admin"] -->|"approvals, generation<br/>jobs, audit reviews"| SYS
    LLMEXT["Groq / Gemini APIs"] <-->|"LLM requests/responses"| SYS
    SYS -->|"answers, citations,<br/>risk insights"| STU
    SYS -->|"auto reports, alerts"| LEC
    SYS -->|"decision cards,<br/>utilization metrics"| ADM
    SYS -->|"metrics"| MON["Prometheus / Grafana / Sentry"]
```

### 10.2 Level 1 DFD

```mermaid
flowchart LR
    ext1["Student"]
    ext2["Lecturer"]
    ext3["Admin"]
    ext4["Groq/Gemini APIs"]
    ext5["Ollama (local)"]

    p0["0.0 Gateway<br/>(auth, RBAC, routing)"]
    p1["1.0 Supervisor<br/>(intent routing)"]
    p2["2.0 Academic Ops<br/>(RAG + registration)"]
    p3["3.0 Student Success<br/>(predict + explain)"]
    p4["4.0 Resource Optimizer<br/>(OR-Tools)"]
    p5["5.0 Knowledge Agent<br/>(NL to Cypher)"]
    p6["6.0 Audit Agent"]
    p7["7.0 Synthetic Generator"]

    d1[("PostgreSQL")]
    d2[("Neo4j")]
    d3[("Qdrant/Chroma")]
    d4[("Redis")]
    d5[("MLflow")]

    ext1 --> p0
    ext2 --> p0
    ext3 --> p0
    p0 --> p1
    p1 --> p2
    p1 --> p3
    p1 --> p4
    p1 --> p5
    p2 --> p3
    p2 --> d3
    p2 --> d1
    p2 --> ext4
    p2 --> ext5
    p3 --> d1
    p3 --> d5
    p3 --> ext4
    p4 --> d1
    p5 --> d2
    p5 --> ext4
    p6 --> p2
    p6 --> p3
    p6 --> p4
    p6 --> p5
    p6 --> d1
    p7 --> d1
    p7 --> d2
    p7 --> d3
    p7 --> p6
    p0 --> d4
    p3 --> ext2
    p4 --> ext3
    p6 --> ext3
    p1 --> p6
    p7 --> ext3
```

### DFD explanation

| Process | Inputs | Outputs | Store touched |
|---|---|---|---|
| **0.0 Gateway** | login, chat messages, job requests | routed intents, tokens, errors | Redis (rate limit, cache) |
| **1.0 Supervisor** | intents from gateway | dispatched agent runs, approval gates | — |
| **2.0 Academic Ops** | questions, registration requests | answers with citations, enrollments, audit events | Postgres, Qdrant/Chroma, LLMs |
| **3.0 Student Success** | feature rows (from Postgres) | risk scores, SHAP explanations, intervention plans, lecturer alerts | Postgres, MLflow |
| **4.0 Resource Optimizer** | course/room/lecturer data | timetable rows, conflict report, utilization metrics | Postgres |
| **5.0 Knowledge Agent** | NL queries | Cypher-generated answers, graph results | Neo4j |
| **6.0 Audit Agent** | events from all processes | append-only logs, Decision Cards, CSV exports | Postgres |
| **7.0 Synthetic Generator** | config (size, seed) | populated datasets in all stores, generation report | Postgres, Neo4j, Qdrant |

All processes emit to 6.0 (audit) — the audit agent is deliberately drawn as a sink connected to every process to make the guarantee explicit.

---

## 11. Cross-Cutting Design Decisions

| Concern | Decision | Why |
|---|---|---|
| LLM failure | Fallback chain Groq → Gemini → Ollama + circuit breaker | Zero-cost + offline resilience; audited provider metadata for the report |
| Retrieval failure | `VectorStore` interface; Qdrant primary, Chroma embedded fallback | Same pipeline code, one config switch |
| Data consistency | Postgres = truth; Neo4j/Qdrant rebuilt from Postgres by Celery sync tasks | No distributed transactions; stale read models are acceptable |
| Audit integrity | Append-only + `prev_hash` chaining | Tamper-evidence without a blockchain's cost |
| Model reproducibility | MLflow version + `models` row + SHAP JSON per prediction | Every prediction is explainable and reproducible at defense time |
| Concurrency | All mutating agent actions serialized per entity via Redis locks | Prevents double-registration races in the FYP demo |
| Security | JWT short-lived access + refresh; bcrypt; RBAC at router level; SSE auth via token query param | Matches NFR security targets; no PII stored (synthetic only) |

---

## 12. Traceability to Phase 1

| Phase 1 item | Phase 2 coverage |
|---|---|
| FR-1 (auth/RBAC) | §2 L2, §4 AuthService, §8 User/Student/Lecturer/Admin, §9 `users` |
| FR-2 (academic ops) | §6.1–6.2, §8 AcademicOpsAgent, §9 enrollments/results |
| FR-3 (prediction) | §6.3, §8 MLEngine/Explainer, §9 predictions/intervention_plans |
| FR-4 (resource opt) | §8 OptimizerService, §9 timetable_entries |
| FR-5 (knowledge graph) | §5, §8 GraphService/KnowledgeAgent, §9 `courses` prereq |
| FR-6 (synthetic data) | §8 SyntheticDataGenerator, §7 DFD p7 |
| FR-7 (audit trail) | §4 AuditService, §8 AuditLog/DecisionCard, §9 hash-chaining, DFD p6 |
| NFR fallback | §5.1 LLM chain, §5.2 Chroma fallback, §7 deployment |
| NFR cost | §7 all heavy services local/self-hosted |

---

## 13. Next Steps

1. Scaffold the monorepo (backend, frontend, docker-compose, CI) — queued.
2. Implement `LLMGateway` + `VectorStore` abstractions first (everything depends on them).
3. Build `SyntheticDataGenerator` and load all stores.
4. Stand up LangGraph supervisor with the four agents + audit interceptor.
