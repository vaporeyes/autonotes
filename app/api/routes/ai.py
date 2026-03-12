# ABOUTME: Routes for AI-powered note analysis and vault chat.
# ABOUTME: POST /ai/analyze dispatches background job, POST /ai/chat is synchronous.

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import llm_error, validation_error
from app.db.session import get_session
from app.models.job import JobType
from app.schemas.ai import AnalyzeRequest, ChatRequest, ChatResponse
from app.services import ai_service, job_service
from app.tasks.ai_analysis import ai_analysis

router = APIRouter(tags=["AI"])

_VALID_ANALYSIS_TYPES = {"suggest_backlinks", "suggest_tags", "generate_summary", "cleanup_targets"}


@router.post("/ai/analyze")
async def analyze(req: AnalyzeRequest, session: AsyncSession = Depends(get_session)):
    if req.analysis_type not in _VALID_ANALYSIS_TYPES:
        raise validation_error(
            f"Invalid analysis_type: {req.analysis_type}. "
            f"Valid types: {', '.join(sorted(_VALID_ANALYSIS_TYPES))}"
        )

    job, _ = await job_service.create_job(
        session,
        job_type=JobType.ai_analysis.value,
        target_path=req.target_path,
        parameters={"analysis_type": req.analysis_type},
    )
    await session.commit()

    result = ai_analysis.delay(str(job.id), req.target_path, req.analysis_type)
    job.celery_task_id = result.id
    await session.commit()

    return JSONResponse(
        status_code=201,
        content={
            "job_id": str(job.id),
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
        },
    )


@router.post("/ai/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    try:
        result = await ai_service.chat(req.question, req.scope, session)
        await session.commit()
    except Exception as exc:
        raise llm_error(f"LLM chat failed: {exc}")

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        llm_provider=result["llm_provider"],
        notes_sent=result["notes_sent"],
    )
