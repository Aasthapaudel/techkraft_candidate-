import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client):
    await client.post("/auth/register", json={"email": "adm@test.com", "password": "pass123"})
    # Manually promote to admin via DB
    async with TestSessionLocal() as db:
        from sqlalchemy import select
        from app.models import User
        user = (await db.execute(select(User).where(User.email == "adm@test.com"))).scalar_one()
        user.role = "admin"
        await db.commit()
    resp = await client.post("/auth/login", json={"email": "adm@test.com", "password": "pass123"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def reviewer_token(client):
    await client.post("/auth/register", json={"email": "rev@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "rev@test.com", "password": "pass123"})
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def reviewer2_token(client):
    await client.post("/auth/register", json={"email": "rev2@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "rev2@test.com", "password": "pass123"})
    return resp.json()["access_token"]


# ── Test 1: Create a candidate (admin) and verify response ───────────────────

@pytest.mark.asyncio
async def test_create_candidate(client, admin_token):
    resp = await client.post(
        "/candidates",
        json={"name": "Test User", "email": "test@example.com", "role_applied": "Engineer", "skills": ["Python"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["status"] == "new"
    assert "Python" in data["skills"]


# ── Test 2: Reviewer cannot see another reviewer's scores ────────────────────

@pytest.mark.asyncio
async def test_reviewer_cannot_see_other_reviewer_scores(client, admin_token, reviewer_token, reviewer2_token):
    # Admin creates a candidate
    resp = await client.post(
        "/candidates",
        json={"name": "Shared Candidate", "email": "shared@example.com", "role_applied": "Dev", "skills": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    candidate_id = resp.json()["id"]

    # Reviewer 1 submits a score
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Technical", "score": 4, "note": "Good"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Reviewer 2 sees the candidate detail — should have ZERO scores
    resp2 = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {reviewer2_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["scores"] == []


# ── Test 3: Admin sees all scores; reviewer only their own ───────────────────

@pytest.mark.asyncio
async def test_admin_sees_all_scores(client, admin_token, reviewer_token, reviewer2_token):
    resp = await client.post(
        "/candidates",
        json={"name": "Multi Scorer", "email": "multi@example.com", "role_applied": "Dev", "skills": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    candidate_id = resp.json()["id"]

    # Both reviewers score
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Technical", "score": 3},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Communication", "score": 5},
        headers={"Authorization": f"Bearer {reviewer2_token}"},
    )

    # Admin sees both
    resp_admin = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert len(resp_admin.json()["scores"]) == 2

    # Reviewer 1 sees only their own (1 score)
    resp_rev = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert len(resp_rev.json()["scores"]) == 1


# ── Test 4: Auth enforcement — unauthenticated request is rejected ───────────

@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/candidates")
    assert resp.status_code == 401


# ── Test 5: Role not accepted from client at registration ────────────────────

@pytest.mark.asyncio
async def test_registration_role_hardcoded_to_reviewer(client):
    # Even if someone sends role=admin, it must be ignored
    resp = await client.post(
        "/auth/register",
        json={"email": "hacker@example.com", "password": "hacked1", "role": "admin"},
    )
    assert resp.status_code == 201
    # Login and check /me
    login = await client.post("/auth/login", json={"email": "hacker@example.com", "password": "hacked1"})
    token = login.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "reviewer"


# ── Test 6: Soft delete — candidate not returned after delete ────────────────

@pytest.mark.asyncio
async def test_soft_delete(client, admin_token):
    resp = await client.post(
        "/candidates",
        json={"name": "To Delete", "email": "del@example.com", "role_applied": "Dev", "skills": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    candidate_id = resp.json()["id"]

    del_resp = await client.delete(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404
