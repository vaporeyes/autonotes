# ABOUTME: Pydantic response schemas for note reading and folder analysis.
# ABOUTME: Note (full parsed content) and NoteSummary (compact folder listing).

from datetime import datetime

from pydantic import BaseModel


class Heading(BaseModel):
    level: int
    text: str
    line: int


class Note(BaseModel):
    file_path: str
    frontmatter: dict
    headings: list[Heading]
    tags: list[str]
    backlinks: list[str]
    word_count: int
    last_modified: datetime
    content_hash: str


class NoteSummary(BaseModel):
    file_path: str
    title: str
    tags: list[str]
    backlink_count: int
    word_count: int
    last_modified: datetime


class FolderResponse(BaseModel):
    folder: str
    note_count: int
    notes: list[NoteSummary]
