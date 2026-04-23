from typing import Literal

from pydantic import BaseModel, Field


class TenderSummary(BaseModel):
    company_details: list[str]
    payment_terms: list[str]
    compliance_requirements: list[str]
    service_scope: list[str]
    submission_formats: list[str]
    notes: list[str]


class TenderProcessingResponse(BaseModel):
    tender_id: str
    organization: str
    source_filename: str
    ocr_used: bool
    extracted: TenderSummary
    needs_human_review: list[str]
    final_output: str


class TenderReviewSaveRequest(BaseModel):
    extracted: TenderSummary
    needs_human_review: list[str] = Field(default_factory=list)
    final_output: str
    reviewer_notes: str = ""
    status: Literal["draft", "final"] = "draft"


class TenderRecord(BaseModel):
    tender_id: str
    organization: str
    source_filename: str
    ocr_used: bool
    extracted: TenderSummary
    needs_human_review: list[str]
    final_output: str
    reviewer_notes: str = ""
    status: Literal["processed", "draft", "final"] = "processed"
    created_at: str
    updated_at: str


class UserRegisterRequest(BaseModel):
    username: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str
    csrf_token: str


class UserProfileResponse(BaseModel):
    id: int
    username: str


class MessageResponse(BaseModel):
    message: str
