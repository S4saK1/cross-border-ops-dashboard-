from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TermCreate(BaseModel):
    zh: str = Field(..., max_length=100)
    en: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50)
    note: Optional[str] = None
    synonyms: list[str] = []
    platform_amazon: Optional[str] = None
    platform_alibaba: Optional[str] = None


class TermUpdate(BaseModel):
    zh: Optional[str] = None
    en: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None
    synonyms: Optional[list[str]] = None
    platform_amazon: Optional[str] = None
    platform_alibaba: Optional[str] = None


class TermOut(BaseModel):
    id: str
    zh: str
    en: str
    category: str
    note: Optional[str] = None
    synonyms: list[str]
    platform_amazon: Optional[str] = None
    platform_alibaba: Optional[str] = None
    is_builtin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TermListResponse(BaseModel):
    items: list[TermOut]
    total: int
    page: int
    page_size: int
    total_pages: int
