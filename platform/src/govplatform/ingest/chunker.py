"""Deterministic Markdown-aware child chunks linked to a knowledge object."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from govplatform.knowledge.models import KnowledgeObject

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_MAX_CHARS = 700
_OVERLAP_CHARS = 80


@dataclass(frozen=True)
class ChildChunk:
    chunk_id: str
    parent_id: str
    parent_version: int
    ordinal: int
    heading_path: tuple[str, ...]
    text: str
    bm25_field: str
    source: str
    content_hash: str

    @property
    def vector_text(self) -> str:
        return self.bm25_field


def _sections(body: str) -> list[tuple[tuple[str, ...], str]]:
    path: list[str] = []
    lines: list[str] = []
    result: list[tuple[tuple[str, ...], str]] = []

    def flush() -> None:
        text = "\n".join(lines).strip()
        if text:
            result.append((tuple(path), text))
        lines.clear()

    for line in body.splitlines():
        match = _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            path = path[: level - 1] + [match.group(2).strip()]
        else:
            lines.append(line)
    flush()
    return result


def _windows(text: str) -> list[str]:
    if len(text) <= _MAX_CHARS:
        return [text]
    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + _MAX_CHARS, len(text))
        if end < len(text):
            paragraph = text.rfind("\n\n", start + _MAX_CHARS // 2, end)
            if paragraph > start:
                end = paragraph
        piece = text[start:end].strip()
        if piece:
            windows.append(piece)
        if end == len(text):
            break
        start = max(start + 1, end - _OVERLAP_CHARS)
    return windows


def chunk_knowledge(obj: KnowledgeObject) -> list[ChildChunk]:
    result: list[ChildChunk] = []
    sections = _sections(obj.body)
    if not sections and obj.body.strip():
        sections = [((), obj.body.strip())]
    for path, section in sections:
        for text in _windows(section):
            ordinal = len(result)
            identity = f"{obj.knowledge_id}:{obj.version}:{obj.content_hash}:{ordinal}"
            chunk_id = hashlib.sha256(identity.encode()).hexdigest()[:32]
            context = " ".join((obj.title, *path, text))
            result.append(
                ChildChunk(
                    chunk_id=chunk_id,
                    parent_id=obj.knowledge_id,
                    parent_version=obj.version,
                    ordinal=ordinal,
                    heading_path=path,
                    text=text,
                    bm25_field=context,
                    source=obj.source,
                    content_hash=obj.content_hash,
                )
            )
    return result
