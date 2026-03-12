# ABOUTME: Idempotent patch engine for surgical note modifications.
# ABOUTME: Applies domain-specific ops (add_tag, add_backlink, etc.) with check-before-write guards.

import hashlib
import json
import re

import frontmatter
from markdown_it import MarkdownIt

from app.models.patch_operation import OperationType, RiskLevel
from app.services.note_parser import compute_content_hash

_WIKILINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|[^\[\]]+)?\]\]")
_TAG_RE = re.compile(r"(?<!\S)#([a-zA-Z][a-zA-Z0-9/_-]*)")
_md = MarkdownIt()

LOW_RISK_OPS = {OperationType.add_tag, OperationType.remove_tag, OperationType.update_frontmatter_key}
HIGH_RISK_OPS = {
    OperationType.add_backlink, OperationType.remove_backlink,
    OperationType.append_body, OperationType.prepend_body,
}


def classify_risk(operation_type: str) -> RiskLevel:
    op = OperationType(operation_type)
    if op in LOW_RISK_OPS:
        return RiskLevel.low
    return RiskLevel.high


def compute_idempotency_key(target_path: str, operation_type: str, payload: dict) -> str:
    data = json.dumps({"path": target_path, "type": operation_type, "payload": payload}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:64]


def apply_patch(raw_content: str, operation_type: str, payload: dict) -> tuple[str, bool]:
    """Apply a single patch operation to raw note content.

    Returns (new_content, changed). If the operation is a no-op
    (e.g. tag already exists), changed is False and content is unchanged.
    """
    op = OperationType(operation_type)

    if op == OperationType.add_tag:
        return _add_tag(raw_content, payload["tag"])
    elif op == OperationType.remove_tag:
        return _remove_tag(raw_content, payload["tag"])
    elif op == OperationType.add_backlink:
        return _add_backlink(raw_content, payload["target"], payload.get("display_text"))
    elif op == OperationType.remove_backlink:
        return _remove_backlink(raw_content, payload["target"])
    elif op == OperationType.update_frontmatter_key:
        return _update_frontmatter_key(raw_content, payload["key"], payload["value"])
    elif op == OperationType.append_body:
        return _append_body(raw_content, payload["content"], payload.get("heading"))
    elif op == OperationType.prepend_body:
        return _prepend_body(raw_content, payload["content"], payload.get("heading"))

    raise ValueError(f"Unknown operation type: {operation_type}")


def _add_tag(content: str, tag: str) -> tuple[str, bool]:
    post = frontmatter.loads(content)
    tags = post.metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if tag in tags:
        return content, False
    tags.append(tag)
    post.metadata["tags"] = tags
    return frontmatter.dumps(post), True


def _remove_tag(content: str, tag: str) -> tuple[str, bool]:
    post = frontmatter.loads(content)
    tags = post.metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if tag not in tags:
        return content, False
    tags.remove(tag)
    post.metadata["tags"] = tags
    return frontmatter.dumps(post), True


def _add_backlink(content: str, target: str, display_text: str | None = None) -> tuple[str, bool]:
    existing = set(m.group(1) for m in _WIKILINK_RE.finditer(content))
    if target in existing:
        return content, False
    link = f"[[{target}|{display_text}]]" if display_text else f"[[{target}]]"
    new_content = content.rstrip() + "\n" + link + "\n"
    return new_content, True


def _remove_backlink(content: str, target: str) -> tuple[str, bool]:
    pattern = re.compile(r"\[\[" + re.escape(target) + r"(?:\|[^\[\]]+)?\]\]")
    new_content, count = pattern.subn("", content)
    if count == 0:
        return content, False
    return new_content, True


def _update_frontmatter_key(content: str, key: str, value) -> tuple[str, bool]:
    post = frontmatter.loads(content)
    if post.metadata.get(key) == value:
        return content, False
    post.metadata[key] = value
    return frontmatter.dumps(post), True


def _find_heading_line_range(body: str, heading: str) -> tuple[int, int] | None:
    tokens = _md.parse(body)
    lines = body.split("\n")
    target_level = None
    start_line = None

    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.map:
            level = int(token.tag[1])
            inline = tokens[i + 1] if i + 1 < len(tokens) else None
            text = inline.content if inline else ""
            heading_text = heading.lstrip("#").strip()
            if text == heading_text:
                target_level = level
                start_line = token.map[1]
                continue
            if target_level is not None and level <= target_level:
                return start_line, token.map[0]

    if start_line is not None:
        return start_line, len(lines)
    return None


def _append_body(content: str, new_content: str, heading: str | None = None) -> tuple[str, bool]:
    if heading is None:
        result = content.rstrip() + "\n\n" + new_content + "\n"
        return result, True

    post = frontmatter.loads(content)
    body = post.content
    line_range = _find_heading_line_range(body, heading)
    if line_range is None:
        body = body.rstrip() + "\n\n" + heading + "\n" + new_content + "\n"
    else:
        lines = body.split("\n")
        insert_at = line_range[1]
        lines.insert(insert_at, new_content)
        body = "\n".join(lines)
    post.content = body
    return frontmatter.dumps(post), True


def _prepend_body(content: str, new_content: str, heading: str | None = None) -> tuple[str, bool]:
    if heading is None:
        post = frontmatter.loads(content)
        post.content = new_content + "\n\n" + post.content
        return frontmatter.dumps(post), True

    post = frontmatter.loads(content)
    body = post.content
    line_range = _find_heading_line_range(body, heading)
    if line_range is None:
        body = body.rstrip() + "\n\n" + heading + "\n" + new_content + "\n"
    else:
        lines = body.split("\n")
        insert_at = line_range[0]
        lines.insert(insert_at, new_content)
        body = "\n".join(lines)
    post.content = body
    return frontmatter.dumps(post), True
