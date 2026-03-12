# ABOUTME: Note parsing service using python-frontmatter and markdown-it-py.
# ABOUTME: Extracts frontmatter, headings, tags, wikilinks, word count, and content hash.

import hashlib
import re
from datetime import datetime, timezone

import frontmatter
from markdown_it import MarkdownIt

from app.schemas.note import Heading, Note, NoteSummary

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]+)?\]\]")
_TAG_RE = re.compile(r"(?<!\S)#([a-zA-Z][a-zA-Z0-9/_-]*)")

_md = MarkdownIt()


def compute_content_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_headings(body: str) -> list[Heading]:
    tokens = _md.parse(body)
    headings = []
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.map:
            level = int(token.tag[1])
            inline = tokens[i + 1] if i + 1 < len(tokens) else None
            text = inline.content if inline else ""
            headings.append(Heading(level=level, text=text, line=token.map[0]))
    return headings


def _extract_tags(post: frontmatter.Post, body: str) -> list[str]:
    tags = set()
    fm_tags = post.metadata.get("tags", [])
    if isinstance(fm_tags, list):
        tags.update(fm_tags)
    elif isinstance(fm_tags, str):
        tags.add(fm_tags)
    for match in _TAG_RE.finditer(body):
        tags.add(match.group(1))
    return sorted(tags)


def _extract_backlinks(body: str) -> list[str]:
    return sorted(set(m.group(1) for m in _WIKILINK_RE.finditer(body)))


def _word_count(body: str) -> int:
    return len(body.split())


def parse_note(file_path: str, raw_content: str, last_modified: datetime | None = None) -> Note:
    post = frontmatter.loads(raw_content)
    body = post.content
    return Note(
        file_path=file_path,
        frontmatter=dict(post.metadata),
        headings=_extract_headings(body),
        tags=_extract_tags(post, body),
        backlinks=_extract_backlinks(body),
        word_count=_word_count(body),
        last_modified=last_modified or datetime.now(timezone.utc),
        content_hash=compute_content_hash(raw_content),
    )


def parse_note_summary(file_path: str, raw_content: str, last_modified: datetime | None = None) -> NoteSummary:
    post = frontmatter.loads(raw_content)
    body = post.content
    tags = _extract_tags(post, body)
    backlinks = _extract_backlinks(body)
    headings = _extract_headings(body)
    title = headings[0].text if headings else file_path.rsplit("/", 1)[-1].removesuffix(".md")
    return NoteSummary(
        file_path=file_path,
        title=title,
        tags=tags,
        backlink_count=len(backlinks),
        word_count=_word_count(body),
        last_modified=last_modified or datetime.now(timezone.utc),
    )
