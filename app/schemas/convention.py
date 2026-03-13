# ABOUTME: Pydantic request/response schemas for folder convention CRUD endpoints.
# ABOUTME: Defines convention creation, update, and resolved (merged) convention responses.

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FrontmatterField(BaseModel):
    key: str
    default_value: Any = None


class ConventionCreate(BaseModel):
    folder_path: str = Field(..., min_length=1)
    required_frontmatter: list[FrontmatterField] = Field(default_factory=list)
    expected_tags: list[str] = Field(default_factory=list)
    backlink_targets: list[str] = Field(default_factory=list)


class ConventionUpdate(BaseModel):
    folder_path: str = Field(..., min_length=1)
    required_frontmatter: list[FrontmatterField] = Field(default_factory=list)
    expected_tags: list[str] = Field(default_factory=list)
    backlink_targets: list[str] = Field(default_factory=list)


class ConventionResponse(BaseModel):
    id: str
    folder_path: str
    required_frontmatter: list[FrontmatterField]
    expected_tags: list[str]
    backlink_targets: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConventionListResponse(BaseModel):
    conventions: list[ConventionResponse]


class ResolvedConvention(BaseModel):
    note_path: str
    merged_from: list[str]
    required_frontmatter: list[FrontmatterField]
    expected_tags: list[str]
    backlink_targets: list[str]
