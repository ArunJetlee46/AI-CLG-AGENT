# PHASE 5 — Backend Development (FastAPI)

> Status: **PARTIALLY IMPLEMENTED** — core CRUD/auth/agents/audit endpoints exist and are tested.
> This document is the authoritative reference: what is built, how it is wired, and the ordered build-out of the remaining work (marked 🔜).

- **Framework:** FastAPI + Pydantic v2 + SQLAlchemy 2.x (sync), `starlette` middleware
- **Auth:** stateless JWTs (`python-jose`), bcrypt password hashing (`passlib`), RBAC role guards
- **Repo:** `backend/app` (see §2); tests run with `pytest` against SQLite
- **Lang:** Python 3.11+ (developed on 3.14, venv at `backend/.venv`)

---

## 1. Goals & scope

| # | Goal | Delivered by |
|---|------|--------------|
| G1 | Boot the API fast, fail loudly, be observable | lifespan bootstrap, `/health`, metrics, Sentry hook |
| G2 | All endpoints authenticated; actions scoped by role | OAuth2 bearer JWT + `require_role` |
| G3 | Stable, machine-readable API surface for the frontend | Pydantic request/response models, consistent errors |
| G4 | Every sensitive action is traceable | audit log written via `record_event` |
| G5 | Agents, ML, vector store accessible behind one facade | route handlers → `services/` → `agents/`/`ml/` |

---

## 2. Folder structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app: middleware, exception handlers, routers, /metrics
│   ├── config.py               # Pydantic Settings (env-driven, cached)
│   ├── db.py                   # SQLAlchemy engine, SessionLocal, get_db, init_db
│   ├── api/
│   │   ├── deps.py             # DI: get_current_user, require_role (OAuth2PasswordBearer)
│   │   └── routes/             # Thin HTTP layer -> one module per domain
│   │       ├── health.py       #   GET /api/v1/health
│   │       ├── auth.py         #   POST login/refresh, GET me, GET roles
│   │       ├── agents.py       #   POST /agents/chat
│   │       ├── audit.py        #   GET list, GET export (CSV), GET decision-cards/{id}
│   │       ├── approvals.py    #   GET list, POST decide
│   │       ├── predictions.py  #   GET list, GET live
│   │       └── synthetic.py    #   POST generate (background task)
│   ├── core/
│   │   ├── security.py         # bcrypt hash/verify, JWT create/decode (access+refresh)
│   │   ├── exceptions.py       # AppError + global handlers + request-context middleware
│   │   └── audit.py            # record_event (append-only, payload hash)
│   ├── schemas/common.py       # Pydantic request/response models (single shared module)
│   ├── models/entities.py      # SQLAlchemy ORM: User, AuditLog, ApprovalRequest, DecisionCard, Prediction, ...
│   ├── agents/                 # LangGraph supervisor + specialist agents (Phase 5 doc §7)
│   ├── services/               # llm.py, rag.py, vector_store.py, graph_service.py (Phases 6–7)
│   ├── ml/                     # train.py, predict.py, features.py, optimize.py (Phase 8)
│   └── workers/                # Celery app + tasks (background batches)
├── tests/                      # pytest + TestClient
├── synthetic/                  # standalone data generator package (Phase 3)
├── requirements.txt
├── Dockerfile
└── pyproject.toml
```

**Layering rule:** `routes/` must not contain business logic — it parses validated models, calls a service/agent/module, and serializes. `services/` and `agents/` hold logic; `models/` holds persistence.

---

## 3. Authentication (stateless JWT)

### 3.1 Credentials & hashing (`core/security.py`)
- Passwords hashed with **bcrypt** (`passlib.CryptContext(schemes=["bcrypt"])`), never stored in plaintext.
- Default admin seeded on startup from env (`DEFAULT_ADMIN_USER` / `DEFAULT_ADMIN_PASSWORD`), role `admin`.

### 3.2 Token design
Two-token model, symmetric HS256, secret from `SECRET_KEY` (env; dev default `dev-secret-change-me` — **must be overridden in prod**).

| Token | Claim highlights | TTL (env) |
|-------|------------------|-----------|
| **access** | `sub` (user id), `role`, `type: access`, `iat`, `exp` | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60) |
| **refresh** | same, `type: refresh` | `REFRESH_TOKEN_EXPIRE_DAYS` (default 7) |

- `create_access_token` / `create_refresh_token` build claims in UTC; `decode_token` raises `ValueError` on invalid/expired → mapped to `401`.
- `token_type` is enforced on decode: an access token is rejected at the refresh endpoint and vice versa (`deps.py` / `auth.py`).

### 3.3 Login flow
1. `POST /api/v1/auth/login` `{username, password}` → lookup user, `verify_password`, check `is_active`.
   - failure → `401`; disabled account → `403`.
2. Returns `TokenResponse {access_token, refresh_token, token_type}`.
3. Frontend stores tokens; sends `Authorization: Bearer <access_token>`.
4. When access expires → `POST /auth/refresh` with refresh token → rotates **both** tokens.

### 3.4 Transport & storage (🔜 hardening)
- Tokens use the `Authorization` header via `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` — standard, Stoplight/OpenAPI friendly.
- Production notes (🔜): require HTTPS; prefer httpOnly/Secure cookie storage over localStorage; add refresh-token rotation + reuse detection table when user sessions matter.

---

## 4. Authorization — RBAC

Three roles (hard-coded, surfaced by `GET /api/v1/auth/roles`): `student`, `lecturer`, `admin`.

Role guard via closure dependency:

```python
# app/api/deps.py
def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
```

### 4.1 Protection matrix

| Endpoint | Auth | Roles |
|----------|------|-------|
| `GET /api/v1/health` | public | — |
| `POST /api/v1/auth/login`, `/auth/refresh` | public | — |
| `GET /auth/me`, `GET /auth/roles` | `get_current_user` / public | any logged-in / any |
| `POST /api/v1/agents/chat` | `get_current_user` | any logged-in |
| `GET /api/v1/audit` | `require_role` | admin, lecturer |
| `GET /api/v1/audit/export` | `require_role` | admin |
| `GET /api/v1/audit/decision-cards/{id}` | `require_role` | admin |
| `GET /api/v1/approvals` | `require_role` | admin |
| `POST /api/v1/approvals/{id}` | `require_role` | admin |
| `GET /api/v1/predictions`, `/predictions/live` | `require_role` | admin, lecturer |
| `POST /api/v1/synthetic/generate` | `require_role` | admin |

**Rule:** every route except public health/login/refresh must list a `Depends` guard — enforced by review + the route-tests in §10 (🔜 add a meta-test that asserts no router route lacks an auth dependency).

---

## 5. REST API catalogue

Conventions: all under `/api/v1/…`; JSON request/response; errors follow the envelope in §7; list endpoints support `limit`/`offset` and filters.

### 5.1 Health & ops
| Method | Path | Request | Response | Purpose |
|--------|------|---------|----------|---------|
| GET | `/api/v1/health` | — | `{status, app, env, db, llm_providers}` | liveness + DB probe |
| GET | `/metrics` | — | Prometheus text | HTTP counters (`beru_http_requests_total`) |

### 5.2 Auth (`routes/auth.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | `/api/v1/auth/login` | `LoginRequest` | `TokenResponse` | 401 bad creds, 403 disabled |
| POST | `/api/v1/auth/refresh` | `RefreshRequest` | `TokenResponse` | 401 invalid/expired/not-a-refresh |
| GET | `/api/v1/auth/me` | — | `UserOut` | current user profile |
| GET | `/api/v1/auth/roles` | — | `{roles:[...]}` | role enum for UI |

### 5.3 Agents (`routes/agents.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | `/api/v1/agents/chat` | `ChatRequest {message}` | `ChatResponse` | supervisor; records audit `chat_completed`; may return `requires_approval` + `approval_id` |

### 5.4 Audit (`routes/audit.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | `/api/v1/audit` | query: `actor,action,entity_type,limit(≤500),offset` | `list[AuditRow]` | newest first |
| GET | `/api/v1/audit/export` | query: `actor` | CSV attachment | admin only |
| GET | `/api/v1/audit/decision-cards/{card_id}` | — | card JSON | admin only |

### 5.5 Approvals (`routes/approvals.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | `/api/v1/approvals` | query: `status` (default `pending`) | `list[{id,intent,payload,status,created_at}]` | admin |
| POST | `/api/v1/approvals/{request_id}` | `ApprovalDecision {decision: approve\|reject, comment}` | result | admin; 404 unknown / 409 conflict |

### 5.6 Predictions (`routes/predictions.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | `/api/v1/predictions` | `limit` | `list[PredictionOut]` | stored predictions |
| GET | `/api/v1/predictions/live` | — | `list[dict]` | on-the-fly scoring + SHAP explanation |

### 5.7 Synthetic data (`routes/synthetic.py`)
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | `/api/v1/synthetic/generate` | `GenerateRequest {students,courses,seed}` | `{status:"queued",...}` | admin; runs as FastAPI `BackgroundTasks`; audit `data_generated` |

### 5.8 Response models (`schemas/common.py`)
| Model | Fields |
|-------|--------|
| `LoginRequest` | `username`, `password` |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type=bearer` |
| `UserOut` | `id`, `username`, `role`, `email` |
| `RefreshRequest` | `refresh_token` |
| `ChatRequest` | `message` (1..4000 chars) |
| `ChatResponse` | `intent`, `agent`, `answer`, `citations[]`, `requires_approval`, `approval_id?`, `decision_card_id?` |
| `ApprovalDecision` | `decision` (regex `approve\|reject`), `comment` |
| `AuditRow` | `id`, `actor`, `action`, `entity_type`, `entity_id?`, `payload`, `hash`, `created_at` |
| `PredictionOut` | `id`, `student_id`, `course_id`, `probability`, `risk_level`, `shap_values`, `model_version`, `created_at` |
| `GenerateRequest` | `students`, `courses`, `seed` |

Validation is enforced at the boundary by Pydantic (types, min/max, regex) → automatic `422` (§7).

---

## 6. Middleware (registration order in `main.py`)

| Layer | What it does |
|-------|--------------|
| **CORS** | allow-all origins (dev). 🔜 tighten to frontend origin list in prod. `allow_credentials=False` (headers only). |
| **`request_context_middleware`** (`core/exceptions.py`) | assigns `X-Request-ID` (client-supplied or generated), logs `request_id method path -> status (ms)`, stamps response header. Failure takes it through exception handlers; unhandled errors surface `request_id` in the body. |
| **`count_requests`** | increments `REQUESTS{method,path,status}` counter for `/metrics`. |
| Exception handlers | registered as **routes' last layer** — see §7. |

🔜 planned: per-route auth logging (actor + request_id into audit/Sentry), simple sliding-window rate limiter keyed by IP/token, `TrustedHostMiddleware`.

---

## 7. Exception handling

**Error envelope:** every error returns `application/json` with at least:
```json
{ "detail": "human-readable message", "code": "stable_machine_code" }
```
`422` additionally returns `errors: [{loc, msg, type}]`; `500` returns `request_id` for correlation.

| Condition | Status | code | Source |
|-----------|--------|------|--------|
| Bad credentials / invalid token | 401 | `http_error` (HTTPException) | `deps.py`, `auth.py` |
| Account disabled | 403 | `http_error` | `auth.py` login |
| Insufficient role | 403 | `http_error` | `require_role` |
| Not found / conflict on approve | 404 / 409 | `http_error` | `approvals.py` |
| Pydantic validation failure | 422 | `validation_error` + `errors[]` | global `RequestValidationError` handler |
| Unhandled exception | 500 | `internal_error` + `request_id` | global `Exception` handler (+ Sentry if `SENTRY_DSN`) |
| Domain error | chosen | `code` | `AppError(status_code, code, detail)` — designed for business conflicts (e.g. duplicate enrollment → `409 enrollment_exists`) 🔜 adopt in services |

Handlers registered in `main.py`: `AppError`, `StarletteHTTPException`, `RequestValidationError`, `Exception`. FastAPI’s dependency chain means `Depends`-raised `HTTPException` bubbles through the standard path automatically.

---

## 8. Dependency injection

FastAPI’s `Depends` is the DI mechanism; no external container needed.

| Dependency | Defined in | Purpose |
|------------|-----------|---------|
| `get_db` | `db.py` | yields a `Session`, guarantees close; per-request scope |
| `oauth2_scheme` | `deps.py` | extracts bearer token (Swagger “Authorize” button) |
| `get_current_user` | `deps.py` | decode + type-check JWT, load user, verify active |
| `require_role(...)` | `deps.py` | composes `get_current_user` + role gate |
| `get_settings()` | `config.py` | cached singleton `Settings` (`@lru_cache`) |

Pattern: `def handler(user: User = Depends(get_current_user), db: Session = Depends(get_db))`. Guards and DB sessions are always injected, never imported/constructed inside handlers — keeps route code declarative and trivially overridable in tests.

---

## 9. Verified behavior

- `pytest` (4 tests) green — health, login→token, authorized chat fallback path.
- Smoke-verified in this repo:
  - `404` → `{"detail":"Not Found","code":"http_error"}`
  - `422` bad body → `{"code":"validation_error","errors":[...]}`
  - `X-Request-ID` attached to every response.

---

## 10. Implementation order (remaining build-out, 🔜)

Do these in order; each step keeps the suite green.

1. **Route-audit meta-test** — auto-assert every `/api/v1` non-public route has an auth `Depends`; fail on regressions.
2. **Adopt `AppError` in services** — replace ad-hoc `HTTPException`/`{"error": ...}` returns with typed domain errors (keeps `code` stable for frontend).
3. **Acceptance tests per endpoint** — table-driven TestClient suite: happy path, 401, 403, 404, 422 for each router (auth, agents, audit, approvals, predictions, synthetic).
4. **RBAC test matrix** — parametrize all three roles × protected endpoints; assert exact status codes.
5. **Refresh-token rotation & revocation** — store token family on `User` (or redis), reject replays. (Needed before real prod users.)
6. **Rate limiting** — IP + token sliding window on `/auth/login` (brute-force) and `/agents/chat` (cost).
7. **CORS/trusted-host hardening** — env-driven allowlist.
8. **OpenAPI contract** — publish `openapi.json` snapshot + schema as a frontend source of truth (contract tests).
9. **Actor-aware logging** — include `request.state.actor` in `request_context_middleware` logs once auth runs before it (reorder or read header).
10. **Sentry + structured logs** to configured collector (already DSN-gated).

### Already done in this phase (this session)
- Added `app/core/exceptions.py` (AppError, 4 global handlers, request-context middleware).
- Wired middleware + exception handlers into `main.py`; `/metrics` retains its own counter.
- Verified behaviour live via TestClient; existing tests still green.

---

## 11. OpenAPI

FastAPI auto-generates schema at `/docs` (Swagger) and `/openapi.json`. Every route carries `tags`; models are Pydantic so the contract is exact. Used by the React frontend (Phase 9) and by the bots/agents only through typed services — never raw parsing.
