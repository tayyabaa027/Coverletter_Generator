"""
Pydantic request/response models.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


class CoverLetterRequest(BaseModel):
    job_title: str = Field(..., max_length=120)
    company_name: str = Field(..., max_length=120)
    job_description: str = Field(..., max_length=4000)
    candidate_background: str = Field(..., max_length=3000)
    tone: Literal["formal", "conversational", "confident"] = "formal"
    word_limit: Optional[int] = Field(default=300, ge=100, le=800,
                                       description="Target word count for the cover letter")
    language: str = Field(default="English", max_length=50,
                           description="Language for the cover letter, e.g. English, Urdu, French")


class HealthResponse(BaseModel):
    status: str
    model: str
