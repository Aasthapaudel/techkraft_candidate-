import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Candidate
from app.schemas import (
    CandidateCreate, CandidateUpdate, CandidateDetail, CandidateListItem,
    PaginatedCandidates, ScoreCreate, ScoreOut,
)
from app.auth import get_current_user, require_admin
from app.services.candidate_service import (
    list_candidates, get_candidate, create_candidate,
    soft_delete_candidate, get_scores_for_candidate,
    add_score, generate_ai_summary,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=PaginatedCandidates)
async def get_candidates(
    status: Optional[str] = Query(None),
    role_applied: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidates, total = await list_candidates(
        db, status=status, role_applied=role_applied,
        skill=skill, keyword=keyword, offset=offset, page_size=page_size,
    )
    return PaginatedCandidates(
        items=candidates, total=total, offset=offset, page_size=page_size
    )


@router.post("", response_model=CandidateDetail, status_code=201)
async def create(
    body: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    data = body.model_dump()
    # Non-admins can't set internal_notes via this path anyway (require_admin above)
    candidate = await create_candidate(db, data)
    return _build_detail(candidate, current_user, scores=[])


@router.get("/{candidate_id}", response_model=CandidateDetail)
async def get_one(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    reviewer_id = None if current_user.role == "admin" else current_user.id
    scores = await get_scores_for_candidate(db, candidate_id, reviewer_id=reviewer_id)
    return _build_detail(candidate, current_user, scores=scores)


@router.patch("/{candidate_id}", response_model=CandidateDetail)
async def update_candidate(
    candidate_id: str,
    body: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if body.internal_notes is not None:
        candidate.internal_notes = body.internal_notes
    if body.status is not None:
        candidate.status = body.status

    await db.flush()
    scores = await get_scores_for_candidate(db, candidate_id)
    return _build_detail(candidate, current_user, scores=scores)


@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await soft_delete_candidate(db, candidate)


@router.post("/{candidate_id}/scores", response_model=ScoreOut, status_code=201)
async def submit_score(
    candidate_id: str,
    body: ScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    score = await add_score(
        db, candidate_id, current_user.id, body.category, body.score, body.note
    )
    return score


@router.post("/{candidate_id}/summary")
async def trigger_summary(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    summary = await generate_ai_summary(candidate)
    candidate.ai_summary = summary
    await db.flush()
    return {"summary": summary}


@router.get("/{candidate_id}/stream")
async def stream_scores(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE endpoint — streams score updates every 3 seconds."""
    candidate = await get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    async def event_generator():
        for _ in range(10):   # stream up to 10 updates then close
            await asyncio.sleep(3)
            reviewer_id = None if current_user.role == "admin" else current_user.id
            scores = await get_scores_for_candidate(db, candidate_id, reviewer_id=reviewer_id)
            payload = [
                {"id": s.id, "category": s.category, "score": s.score, "note": s.note}
                for s in scores
            ]
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_detail(candidate: Candidate, current_user: User, scores=None) -> dict:
    return CandidateDetail(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        role_applied=candidate.role_applied,
        status=candidate.status,
        skills=candidate.skills or [],
        internal_notes=candidate.internal_notes if current_user.role == "admin" else None,
        ai_summary=candidate.ai_summary,
        scores=scores if scores is not None else candidate.scores,
        created_at=candidate.created_at,
    )
