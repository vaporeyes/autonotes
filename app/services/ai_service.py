# ABOUTME: AI service for LLM-powered note analysis, suggestions, and chat.
# ABOUTME: Sends note content to LLM only on explicit user request, logs all interactions.

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_interaction import LLMInteraction
from app.services.llm_provider import LLMProvider, get_llm_provider
from app.services.note_parser import parse_note
from app.services.obsidian_client import ObsidianClient
from app.services.prompts import ANALYSIS_PROMPTS, CHAT_PROMPT


async def analyze(
    target_path: str,
    analysis_type: str,
    session: AsyncSession,
    client: ObsidianClient | None = None,
    provider: LLMProvider | None = None,
) -> dict:
    client = client or ObsidianClient()
    provider = provider or get_llm_provider()
    should_close = client is not None

    try:
        files = await client.list_folder(target_path)
        md_files = [f for f in files if f.endswith(".md")]

        notes_content = []
        note_paths = []
        for fp in md_files[:50]:
            try:
                raw = await client.get_note_raw(fp)
                notes_content.append(f"--- {fp} ---\n{raw}")
                note_paths.append(fp)
            except Exception:
                continue

        system_prompt = ANALYSIS_PROMPTS.get(analysis_type, ANALYSIS_PROMPTS["cleanup_targets"])
        user_message = "\n\n".join(notes_content)

        response_text, prompt_tokens, completion_tokens = await provider.complete(system_prompt, user_message)

        interaction = LLMInteraction(
            job_id=None,
            provider=provider.provider_name,
            model=provider.model_name,
            notes_sent=note_paths,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        session.add(interaction)
        await session.flush()

        try:
            suggestions = json.loads(response_text)
        except json.JSONDecodeError:
            suggestions = response_text

        return {
            "analysis_type": analysis_type,
            "target_path": target_path,
            "notes_analyzed": len(note_paths),
            "suggestions": suggestions,
            "llm_provider": provider.provider_name,
            "notes_sent": note_paths,
        }
    finally:
        if should_close:
            await client.close()


async def chat(
    question: str,
    scope: str | None,
    session: AsyncSession,
    client: ObsidianClient | None = None,
    provider: LLMProvider | None = None,
) -> dict:
    client = client or ObsidianClient()
    provider = provider or get_llm_provider()
    should_close = client is not None

    try:
        search_results = await client.search(question)
        note_paths = []
        notes_content = []

        for result in search_results[:10]:
            fp = result.get("filename", "")
            if scope and not fp.startswith(scope):
                continue
            try:
                raw = await client.get_note_raw(fp)
                notes_content.append(f"--- {fp} ---\n{raw}")
                note_paths.append(fp)
            except Exception:
                continue

        user_message = f"Question: {question}\n\nNotes:\n" + "\n\n".join(notes_content)
        response_text, prompt_tokens, completion_tokens = await provider.complete(CHAT_PROMPT, user_message)

        interaction = LLMInteraction(
            job_id=None,
            provider=provider.provider_name,
            model=provider.model_name,
            notes_sent=note_paths,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        session.add(interaction)
        await session.flush()

        return {
            "answer": response_text,
            "sources": note_paths,
            "llm_provider": provider.provider_name,
            "notes_sent": note_paths,
        }
    finally:
        if should_close:
            await client.close()
