# TechKraft Recruitment Dashboard

Internal candidate scoring and review dashboard for TechKraft's recruitment workflow.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose

### Quick Start

1. **Clone the repository:**
```bash
git clone git@github.com:Aasthapaudel/techkraft_candidate-.git
cd techkraft
```

2. **Setup environment:**
```bash
cp .env.example .env          # uses sensible defaults for local dev
```

3. **Launch with Docker:**
```bash
docker compose up --build
```

- **Frontend:** http://localhost:5173  
- **Backend API:** http://localhost:8000  
- **API Docs:** http://localhost:8000/docs

### Option B — Run locally without Docker

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend (new terminal):**
```bash
cd frontend
npm install
npm run dev
```

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@techkraft.com | admin123 |
| Reviewer | reviewer@techkraft.com | review123 |

> Seed data (6 sample candidates) is loaded automatically on first startup.

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

6 tests covering: create candidate, reviewer isolation, admin visibility, auth enforcement, role hardcoding, and soft delete.

---

## Example API Calls (curl)

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techkraft.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. List candidates
curl http://localhost:8000/candidates \
  -H "Authorization: Bearer $TOKEN"

# 3. Filter candidates
curl "http://localhost:8000/candidates?status=new&skill=React&page_size=5" \
  -H "Authorization: Bearer $TOKEN"

# 4. Get candidate detail
curl http://localhost:8000/candidates/<ID> \
  -H "Authorization: Bearer $TOKEN"

# 5. Submit a score
curl -X POST http://localhost:8000/candidates/<ID>/scores \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"Technical","score":4,"note":"Strong Python fundamentals"}'

# 6. Trigger AI summary (takes ~2s)
curl -X POST http://localhost:8000/candidates/<ID>/summary \
  -H "Authorization: Bearer $TOKEN"

# 7. Register new reviewer (role is always hardcoded to reviewer)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newreviewer@test.com","password":"pass1234"}'
```

---

## Debugging Signal — Bug Identification

```python
# Buggy version from the assignment
def search_candidates(status: str, keyword: str, page: int, page_size: int):
    all_candidates = db.execute("SELECT * FROM candidates").fetchall()
    filtered = [c for c in all_candidates if c["status"] == status]
    offset = (page - 1) * page_size
    return filtered[offset : offset + page_size]
```

### What's wrong

**The bug is fetching all rows into Python memory before filtering and paginating.**

Three concrete problems:

1. **Full table scan on every request.** `SELECT * FROM candidates` transfers every row regardless of filters. At 10k candidates this wastes significant memory and bandwidth; at 100k+ it causes OOM crashes or extreme latency.

2. **Pagination is applied to the already-filtered Python list, not the DB result.** This means `total` is unknowable without fetching everything, and page numbers shift as data grows — page 2 today might return different rows tomorrow if new candidates are inserted.

3. **Filtering in Python bypasses DB indexes.** An index on `candidates.status` is completely ignored because the WHERE clause never reaches the database.

### Correct approach (implemented in `candidate_service.py`)

```python
async def list_candidates(db, status, keyword, offset, page_size):
    query = select(Candidate).where(Candidate.deleted_at.is_(None))
    if status:
        query = query.where(Candidate.status == status)   # uses DB index
    if keyword:
        query = query.where(or_(
            Candidate.name.ilike(f"%{keyword}%"),
            Candidate.email.ilike(f"%{keyword}%"),
        ))
    # COUNT before slicing — one query, not a full scan
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    # Pagination pushed into SQL
    query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(page_size)
    rows = (await db.execute(query)).scalars().all()
    return rows, total
```

The DB does the work. Only the requested page travels over the wire.

---

## Architecture Decision Records

### ADR 1 — FastAPI over Flask or Django REST

**Context:** Need an async-capable Python API with auto-generated docs and type safety.

**Decision:** FastAPI with async SQLAlchemy (aiosqlite for dev, swappable to PostgreSQL).

**Trade-off:** FastAPI's async model requires discipline — mixing sync DB calls inside async routes causes thread-pool starvation. We used `AsyncSession` throughout to stay consistent. The trade-off accepted is a steeper learning curve vs. Flask's simplicity, but the built-in OpenAPI docs, Pydantic validation, and native async support justify it for a system that will grow to handle concurrent review sessions.

---

### ADR 2 — SQLite for development, schema designed for PostgreSQL migration

**Context:** Needed a database that runs with zero infrastructure locally (Docker Compose without a DB container) but can graduate to a production-grade store.

**Decision:** SQLite via `aiosqlite` for development. The SQLAlchemy ORM layer means a one-line `DATABASE_URL` swap to PostgreSQL in production. Indexes are declared on `candidates.status`, `candidates.role_applied`, and `scores.candidate_id` — these matter in PostgreSQL and are expressed in the schema today.

**Trade-off:** SQLite's JSON column support (for `skills`) is more limited than PostgreSQL's `jsonb`. Skill filtering uses a string `contains` check instead of a proper JSON operator. This is acceptable for development but the service layer comment flags it for production migration.

---

### ADR 3 — JWT with hardcoded role assignment at registration

**Context:** The system has two roles (admin, reviewer) with meaningfully different data access. A common security mistake is accepting `role` from the client at registration.

**Decision:** The `RegisterRequest` schema does not include a `role` field. The `register` endpoint hardcodes `role="reviewer"`. Admin accounts must be created directly (DB seed or a separate admin CLI command). JWTs embed the role so every authenticated request carries it without an extra DB lookup.

**Trade-off:** There's no self-service admin creation flow — an existing admin (or a migration script) must promote users. This is the correct trade-off: convenience loses to security. The alternative (accepting role from the client) would let any user register as admin by sending `{"role": "admin"}` — a critical privilege escalation vulnerability.

---

## Learning Reflection

This project was a good opportunity to practise combining `AsyncSession` in SQLAlchemy 2.0 with FastAPI's dependency injection — the `get_db` generator pattern keeps transactions scoped correctly per request without manual session management in route handlers. Given more time, I would explore replacing the mock AI summary with a real streaming LLM call via the Anthropic API, piped through the SSE endpoint so the frontend can display tokens as they arrive rather than waiting for a full 2-second response.

---

## Project Structure

```
/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          # FastAPI app, lifespan, CORS, seed
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── auth.py          # JWT creation, password hashing, dependencies
│   │   ├── database.py      # Async engine, session factory
│   │   ├── routers/
│   │   │   ├── auth.py      # /auth/register, /auth/login, /auth/me
│   │   │   └── candidates.py # All /candidates/* endpoints
│   │   └── services/
│   │       └── candidate_service.py  # Business logic, DB queries
│   └── tests/
│       └── test_api.py      # 6 pytest-asyncio tests
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx              # Router + PrivateRoute
        ├── styles.css           # All styles
        ├── main.jsx
        ├── api/
        │   └── client.js        # Fetch wrapper, token handling
        ├── components/
        │   └── AuthContext.jsx  # Auth state provider
        └── pages/
            ├── LoginPage.jsx
            ├── CandidatesPage.jsx      # List + filters + pagination
            └── CandidateDetailPage.jsx # Detail + scoring + AI summary + admin panel
```

---

## Security Notes

- Credentials are **never** committed — use `.env.example` as a template
- `SECRET_KEY` defaults to a dev placeholder; **must** be overridden in production
- Role is **never** accepted from the client at registration
- Deleted candidates use soft-delete (`deleted_at` timestamp) — no hard deletes
- Reviewer can only see their own scores; admin sees all — enforced server-side, not just UI
