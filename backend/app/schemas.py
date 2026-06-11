from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    # role is intentionally NOT accepted here — always hardcoded to "reviewer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Score ───────────────────────────────────────────────────────────────────

class ScoreCreate(BaseModel):
    category: str = Field(min_length=1)
    score: int = Field(ge=1, le=5)
    note: Optional[str] = None


class ScoreOut(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Candidate ────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    role_applied: str
    skills: List[str] = []
    internal_notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    internal_notes: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"new", "reviewed", "hired", "rejected", "archived"}
        if v and v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class CandidateListItem(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CandidateDetail(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    internal_notes: Optional[str]   # only populated for admins
    ai_summary: Optional[str]
    scores: List[ScoreOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedCandidates(BaseModel):
    items: List[CandidateListItem]
    total: int
    offset: int
    page_size: int
