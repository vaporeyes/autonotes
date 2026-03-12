# ABOUTME: Pydantic request/response schemas for AI operations.
# ABOUTME: AnalyzeRequest for background analysis, ChatRequest/ChatResponse for sync chat.

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    target_path: str
    analysis_type: str  # suggest_backlinks, suggest_tags, generate_summary, cleanup_targets


class ChatRequest(BaseModel):
    question: str
    scope: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    llm_provider: str
    notes_sent: list[str]
