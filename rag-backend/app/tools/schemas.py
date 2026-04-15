from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SearchCompanyKbArgs(BaseModel):
    query: str = Field(..., min_length=1, description="Search query for the company knowledge base")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")


class SendEmailArgs(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    confirm: bool = Field(
        False,
        description="Must be true to actually send via SMTP (unless server enables EMAIL_SEND_ENABLED)",
    )
