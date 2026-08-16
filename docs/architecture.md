# Beru Campus AI - Architecture Documentation

## System Overview

Beru Campus AI is a multi-tenant, role-based campus intelligence platform with three primary user personas:
- **Students** - Academic copilot, success analytics, AI-powered tools
- **Faculty** - Course management, intervention system, AI teaching assistants
- **Placement Officers** - Drive management, job matching, analytics

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend (React + TypeScript + Vite)"
        UI[React SPA]
        State[Zustand + TanStack Query]
        Components[Shared UI Components]
    end

    subgraph "Backend (FastAPI + Python)"
        API[REST API]
        Auth[JWT Auth + RBAC]
        Routes[API Routes]
        Services[Domain Services]
        Agents[LangGraph Multi-Agent System]
        Workers[Celery Workers]
    end

    subgraph "Data Layer"
        Postgres[(PostgreSQL\nPrimary Data)]
        Redis[(Redis\nCache + Queue)]
        Neo4j[(Neo4j\nGraph DB)]
        Qdrant[(Qdrant\nVector DB)]
        MLflow[(MLflow\nModel Tracking)]
    end

    subgraph "External Services"
        Ollama[Ollama Local LLM]
        Groq[Groq API]
        Gemini[Gemini API]
    end

    UI -->|HTTPS| API
    API --> Postgres
    API --> Redis
    API --> Neo4j
    API --> Qdrant
    API --> MLflow
    Workers --> Redis
    Workers --> Postgres
    Agents --> Services
    Agents --> Ollama
    Agents --> Groq
    Agents --> Gemini
    Services --> Postgres
    Services --> Neo4j
    Services --> Qdrant
    Services --> Redis
```

---

## Backend Architecture

### Module Structure

```mermaid
graph TD
    Main[main.py] --> Config[config.py]
    Main --> DB[db.py]
    Main --> Lifespan[Lifespan Events]
    
    Lifespan --> SeedAdmin[Seed Admin]
    Lifespan --> SeedUsers[Seed Demo Users]
    Lifespan --> SeedKB[Seed Knowledge Base]
    Lifespan --> SeedCurriculum[Seed Curriculum KB]
    
    API[API Routes] --> Auth[auth.py]
    API --> Students[students.py]
    API --> Faculty[faculty.py]
    API --> Placement[placement.py]
    API --> Agents[agents.py]
    API --> Admin[admin_module.py]
    API --> Health[health.py]
    API --> Predictions[predictions.py]
    API --> Notifications[notifications.py]
    API --> Approvals[approvals.py]
    API --> Audit[audit.py]
    API --> Synthetic[synthetic.py]
    
    Services[Services] --> StudentsSvc[students.py]
    Services --> StudentGrowth[student_growth.py]
    Services --> StudentTools[student_tools.py]
    Services --> FacultySvc[faculty.py]
    Services --> FacultyIntel[faculty_intelligence.py]
    Services --> FacultyTools[faculty_tools.py]
    Services --> PlacementSvc[placement.py]
    Services --> PlacementIntel[placement_intelligence.py]
    Services --> Prereqs[prereqs.py]
    Services --> Pipeline[pipeline.py]
    Services --> RAG[rag.py]
    Services --> CurriculumRAG[curriculum_rag.py]
    Services --> VectorStore[vector_store.py]
    Services --> LLM[llm.py]
    Services --> Notifications[notifications.py]
    Services --> Graph[graph_service.py]
    Services --> ML[predict.py]
    
    Agents[LangGraph Agents] --> Supervisor[supervisor.py]
    Agents --> Base[base.py]
    Agents --> Academic[academic_ops.py]
    Agents --> Specialists[specialists.py]
    Agents --> Debate[debate.py]
    Agents --> Execute[execute.py]
    Agents --> Memory[memory.py]
    Agents --> State[state.py]
    
    ML[ML Pipeline] --> Train[train.py]
    ML --> Predict[predict.py]
    ML --> Features[features.py]
    ML --> Models[models.py]
    ML --> Optimize[optimize.py]
    ML --> Datasets[datasets.py]
```

### Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant Middleware
    participant Router
    participant Service
    participant DB
    participant Agent
    participant LLM
    
    Client->>Middleware: HTTP Request
    Middleware->>Middleware: CORS, Auth, Metrics
    Middleware->>Router: Route to handler
    Router->>Service: Call domain service
    Service->>DB: Query/Command
    DB-->>Service: Results
    Service-->>Router: Domain response
    Router-->>Client: JSON Response
    
    Note over Client,Agent: Agent Chat Flow
    Client->>Router: POST /agents/chat
    Router->>Agent: Supervisor.invoke()
    Agent->>Agent: Memory → Router → Planner
    Agent->>Agent: Specialist (conditional)
    Agent->>LLM: LLM Gateway (Ollama/Groq/Gemini)
    LLM-->>Agent: Response
    Agent->>Agent: Reflect → Debate → Terminal
    Agent-->>Router: AgentState
    Router-->>Client: ChatResponse
```

---

## Multi-Agent System (LangGraph)

### Supervisor Graph

```mermaid
stateDiagram-v2
    [*] --> Memory
    Memory --> Router
    Router --> Planner
    Planner --> Academic: intent=academic
    Planner --> Success: intent=success
    Planner --> Resources: intent=resources
    Planner --> Knowledge: intent=knowledge
    
    Academic --> Reflect
    Success --> Reflect
    Resources --> Reflect
    Knowledge --> Reflect
    
    Reflect --> Debate: intent=success
    Reflect --> Terminal: otherwise
    Debate --> Terminal
    Terminal --> [*]
```

### Agent Specializations

| Agent | Responsibility | Tools |
|-------|---------------|-------|
| **AcademicOps** | Course ops, enrollment, timetable | SQL, Prereq Graph |
| **StudentSuccess** | Risk prediction, interventions | ML Models, Analytics |
| **ResourceOptimizer** | Room allocation, scheduling | OR-Tools, Neo4j |
| **Knowledge** | Curriculum RAG, graph queries | Qdrant, Neo4j, Cypher |

### Reflection & Debate Nodes

```mermaid
flowchart TD
    Reflect[Reflect Node] --> Checks{Validation Checks}
    Checks --> Empty[Empty Answer?]
    Checks --> Uncertainty[Admitted Uncertainty?]
    Checks --> Approval[Requires Approval?]
    Checks --> Citations[Has Citations?]
    
    Empty -.->|Yes| Conf[Confidence -= 0.40]
    Uncertainty -.->|Yes| Conf2[Confidence -= 0.15]
    Approval -.->|Yes| Conf3[Confidence = min(0.70)]
    Citations -.->|No| Conf4[Confidence -= 0.10]
    
    Conf --> Output[Findings + Confidence]
    Conf2 --> Output
    Conf3 --> Output
    Conf4 --> Output
    
    Output --> Debate{intent=success?}
    Debate -->|Yes| DebateNode[Debate Node]
    Debate -->|No| Terminal[Terminal Node]
    DebateNode --> Terminal
```

---

## RAG Pipeline

```mermaid
flowchart TD
    Query[User Query] --> Router{Route Query}
    Router -->|Curriculum| CurriculumRAG[Curriculum RAG]
    Router -->|General| GeneralRAG[General Knowledge RAG]
    
    CurriculumRAG --> Chunk[Chunk Documents]
    Chunk --> Embed[Embed with nomic-embed-text]
    Embed --> VectorStore[Qdrant Vector Store]
    VectorStore --> Search[Vector Search]
    
    GeneralRAG --> Keyword[Keyword Index]
    Keyword --> Hybrid[Hybrid Search]
    Hybrid --> Rerank[Cross-Encoder Rerank]
    Rerank --> Context[Build Context]
    
    Search --> Rerank
    Context --> LLM[LLM Gateway]
    LLM --> Provider{Provider Order}
    Provider -->|1st| Ollama[Ollama: llama3.2:3b]
    Provider -->|2nd| Groq[Groq: llama-3.3-70b]
    Provider -->|3rd| Gemini[Gemini: 2.0-flash]
    
    Ollama -.->|Fail| Groq
    Groq -.->|Fail| Gemini
    LLM --> Answer[Grounded Answer + Citations]
```

---

## Database Schema (Key Entities)

```mermaid
erDiagram
    USER ||--o| STUDENT : has
    USER ||--o| LECTURER : has
    USER ||--o| ADMIN : has
    
    STUDENT ||--o{ ENROLLMENT : enrolls
    COURSE ||--o{ ENROLLMENT : has
    ENROLLMENT ||--o| RESULT : produces
    ENROLLMENT ||--o{ ATTENDANCE_RECORD : tracks
    
    COURSE }|--o{ COURSE : prerequisites
    
    COMPANY ||--o{ JOB_DESCRIPTION : posts
    JOB_DESCRIPTION ||--o{ PLACEMENT_DRIVE : creates
    PLACEMENT_DRIVE ||--o{ RECRUITMENT_ROUND : has
    PLACEMENT_DRIVE ||--o{ PLACEMENT_SELECTION : records
    STUDENT ||--o{ PLACEMENT_SELECTION : participates
    
    USER ||--o{ INTERVENTION_PLAN : creates
    STUDENT ||--o{ INTERVENTION_PLAN : targets
    
    USER ||--o{ APPROVAL_REQUEST : submits
    APPROVAL_REQUEST ||--o{ AUDIT_LOG : audits
    AUDIT_LOG ||--o| DECISION_CARD : documents
    
    STUDENT ||--o{ PREDICTION : receives
    COURSE ||--o{ PREDICTION : predicts
```

---

## Data Flow: Student Success Score

```mermaid
flowchart LR
    subgraph Input
        Profile[Student Profile]
        Courses[Course Data]
        Attendance[Attendance Records]
        Grades[Grade History]
    end
    
    subgraph Compute
        AttendanceComp[Attendance Component\nweight: 30%]
        AcademicComp[Academic Component\nweight: 45%]
        ConsistencyComp[Consistency Component\nweight: 25%]
    end
    
    subgraph Output
        Score[Success Score 0-100]
        Risk[Risk Level: Low/Med/High]
        Drivers[Key Drivers]
    end
    
    Profile --> AcademicComp
    Courses --> AcademicComp
    Grades --> AcademicComp
    Attendance --> AttendanceComp
    Grades --> ConsistencyComp
    
    AttendanceComp --> Score
    AcademicComp --> Score
    ConsistencyComp --> Score
    
    Score --> Risk
    Score --> Drivers
```

---

## Placement Intelligence Flow

```mermaid
flowchart TD
    JD[Job Description] --> Analyze[JD Analysis\nExtract Skills/Requirements]
    Analyze --> Match[Candidate Matching\nVector + Filter]
    Match --> Score[Scoring Algorithm\nGPA + Skills + Experience]
    Score --> Shortlist[Shortlist Generation]
    Shortlist --> Drive[Placement Drive]
    Drive --> Rounds[Recruitment Rounds]
    Rounds --> Selection[Selections + Offers]
    Selection --> Analytics[Analytics\nFunnel, Salary, Skills]
    
    Students[Student Pool] --> Match
    Companies[Company CRM] --> Drive
```

---

## ML Pipeline

```mermaid
flowchart LR
    subgraph Training
        Raw[Raw Student Data] --> Features[Feature Engineering]
        Features --> Train[Model Training\nXGBoost/LightGBM]
        Train --> Evaluate[Evaluation\nAUC, Precision, Recall]
        Evaluate --> Register[MLflow Model Registry]
        Register --> Promote[Promote to Production]
    end
    
    subgraph Serving
        Promote --> Serve[FastAPI /predict]
        Serve --> Batch[Batch Predictions]
        Serve --> Live[Live Predictions]
        Batch --> Store[Prediction Table]
        Live --> API[Real-time API]
    end
    
    subgraph Monitoring
        Store --> Drift[Drift Detection]
        Drift --> Retrain[Retrain Trigger]
        Retrain --> Features
    end
```

---

## Security Architecture

```mermaid
flowchart TD
    Client[Client] --> TLS[TLS Termination]
    TLS --> CORS[CORS Middleware]
    CORS --> Auth[JWT Authentication]
    Auth --> RBAC[Role-Based Access]
    RBAC --> RateLimit[Rate Limiting]
    RateLimit --> Routes[API Routes]
    
    Routes -->|Student| StudentAPI[/students/*]
    Routes -->|Faculty| FacultyAPI[/faculty/*]
    Routes -->|Placement| PlacementAPI[/placement/*]
    Routes -->|Admin| AdminAPI[/admin/*]
    
    Auth --> TokenGen[Access + Refresh Tokens]
    TokenGen --> Store[HttpOnly Cookies / Header]
    Store --> Validate[Token Validation]
    Validate --> Claims[Extract Claims]
    Claims --> Permissions[Check Permissions]
```

---

## Deployment Architecture (Docker Compose)

```mermaid
graph TB
    subgraph "Docker Network"
        Frontend[Frontend:5173\nNginx + React]
        Backend[Backend:8000\nFastAPI + Uvicorn]
        Worker[Worker\nCelery]
        
        Postgres[(PostgreSQL:5432)]
        Redis[(Redis:6379)]
        Neo4j[(Neo4j:7474/7687)]
        Qdrant[(Qdrant:6333)]
        MLflow[(MLflow:5000)]
        Ollama[(Ollama:11434)]
        
        Prometheus[Prometheus:9090]
        Grafana[Grafana:3000]
    end
    
    Frontend -->|Proxy /api| Backend
    Backend --> Postgres
    Backend --> Redis
    Backend --> Neo4j
    Backend --> Qdrant
    Backend --> MLflow
    Backend -->|LLM| Ollama
    Worker --> Redis
    Worker --> Postgres
    
    Prometheus -->|Scrape| Backend
    Prometheus -->|Scrape| Worker
    Grafana -->|Query| Prometheus
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **LangGraph for Agents** | Explicit state machines, auditability, human-in-the-loop |
| **Hybrid RAG (Keyword + Vector)** | Better recall for curriculum-specific queries |
| **Neo4j for Prerequisites** | Natural graph representation, efficient traversal |
| **Celery for Async** | Reliable task queue, retries, scheduling |
| **MLflow for Models** | Experiment tracking, versioning, deployment |
| **Zustand + TanStack Query** | Lightweight state, server cache synchronization |
| **UUID Primary Keys** | Distributed-friendly, no sequence conflicts |
| **Audit Log + Decision Cards** | Full traceability for compliance/grading |

---

## Future Extensibility Points

1. **Plugin System** - New agent specialists via LangGraph nodes
2. **Webhook Framework** - External integrations (LMS, HRIS)
3. **Multi-Tenancy** - Schema-per-tenant or row-level security
4. **Event Sourcing** - Full audit trail with event replay
5. **GraphQL Gateway** - Flexible data fetching for mobile apps
6. **Real-time** - WebSocket for live dashboards/notifications

---

*Generated for Beru Campus AI Final Year Project*