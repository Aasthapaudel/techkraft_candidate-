import asyncio
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timezone

from app.models import Candidate, Score, User


async def list_candidates(
    db: AsyncSession,
    status: Optional[str] = None,
    role_applied: Optional[str] = None,
    skill: Optional[str] = None,
    keyword: Optional[str] = None,
    offset: int = 0,
    page_size: int = 20,
) -> Tuple[List[Candidate], int]:
    """
    Correct approach: push all filtering + pagination into the DB query.
    This avoids the bug of loading all rows into Python memory.
    """
    query = select(Candidate).where(Candidate.deleted_at.is_(None))

    if status:
        query = query.where(Candidate.status == status)
    if role_applied:
        query = query.where(Candidate.role_applied.ilike(f"%{role_applied}%"))
    if keyword:
        query = query.where(
            or_(
                Candidate.name.ilike(f"%{keyword}%"),
                Candidate.email.ilike(f"%{keyword}%"),
                Candidate.role_applied.ilike(f"%{keyword}%"),
            )
        )
    # skill filter: SQLite JSON contains check
    if skill:
        query = query.where(Candidate.skills.contains(skill))

    # count before pagination
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    candidates = result.scalars().all()
    return candidates, total


async def get_candidate(db: AsyncSession, candidate_id: str) -> Optional[Candidate]:
    result = await db.execute(
        select(Candidate).where(
            and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def create_candidate(db: AsyncSession, data: dict) -> Candidate:
    candidate = Candidate(**data)
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return candidate


async def soft_delete_candidate(db: AsyncSession, candidate: Candidate) -> Candidate:
    candidate.deleted_at = datetime.now(timezone.utc)
    candidate.status = "archived"
    await db.flush()
    return candidate


async def get_scores_for_candidate(
    db: AsyncSession,
    candidate_id: str,
    reviewer_id: Optional[str] = None,
) -> List[Score]:
    query = select(Score).where(Score.candidate_id == candidate_id)
    if reviewer_id:
        query = query.where(Score.reviewer_id == reviewer_id)
    query = query.order_by(Score.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def add_score(
    db: AsyncSession,
    candidate_id: str,
    reviewer_id: str,
    category: str,
    score: int,
    note: Optional[str] = None,
) -> Score:
    s = Score(
        candidate_id=candidate_id,
        reviewer_id=reviewer_id,
        category=category,
        score=score,
        note=note,
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


async def generate_ai_summary(candidate: Candidate) -> str:
    """Mock AI summary — simulates a 2-second async LLM call."""
    await asyncio.sleep(2)
    skills_str = ", ".join(candidate.skills) if candidate.skills else "various skills"
    return (
        f"{candidate.name} is applying for the {candidate.role_applied} role. "
        f"They bring expertise in {skills_str}. "
        f"Current status: {candidate.status}. "
        f"Based on the profile, this candidate appears to be a strong contender "
        f"with a well-rounded background. Recommend proceeding to technical interview."
    )
