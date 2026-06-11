from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db, AsyncSessionLocal
from app.routers import auth, candidates
from app.models import User, Candidate
from app.auth import hash_password
from sqlalchemy import select


async def seed_data():
    """Seed default admin + sample candidates on first run."""
    async with AsyncSessionLocal() as db:
        # Admin user
        admin = (await db.execute(select(User).where(User.email == "admin@techkraft.com"))).scalar_one_or_none()
        if not admin:
            db.add(User(email="admin@techkraft.com", hashed_password=hash_password("admin123"), role="admin"))

        # Reviewer user
        reviewer = (await db.execute(select(User).where(User.email == "reviewer@techkraft.com"))).scalar_one_or_none()
        if not reviewer:
            db.add(User(email="reviewer@techkraft.com", hashed_password=hash_password("review123"), role="reviewer"))

        # Sample candidates
        existing = (await db.execute(select(Candidate))).scalars().first()
        if not existing:
            candidates_data = [
                Candidate(name="Alice Johnson", email="alice@example.com", role_applied="Senior Frontend Engineer",
                          status="new", skills=["React", "TypeScript", "CSS", "GraphQL"]),
                Candidate(name="Bob Martinez", email="bob@example.com", role_applied="Backend Engineer",
                          status="reviewed", skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
                          internal_notes="Strong system design fundamentals. Recommend fast-track."),
                Candidate(name="Carol Chen", email="carol@example.com", role_applied="Full Stack Engineer",
                          status="new", skills=["React", "Node.js", "MongoDB", "AWS"]),
                Candidate(name="David Kim", email="david@example.com", role_applied="DevOps Engineer",
                          status="hired", skills=["Kubernetes", "Terraform", "CI/CD", "AWS"]),
                Candidate(name="Eva Brown", email="eva@example.com", role_applied="Senior Frontend Engineer",
                          status="rejected", skills=["Vue.js", "JavaScript", "Sass"]),
                Candidate(name="Frank Wilson", email="frank@example.com", role_applied="Backend Engineer",
                          status="new", skills=["Go", "gRPC", "Redis", "Kafka"]),
            ]
            for c in candidates_data:
                db.add(c)

        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_data()
    yield


app = FastAPI(title="TechKraft Recruitment API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(candidates.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
