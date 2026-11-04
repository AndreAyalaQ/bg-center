"""Chunk parsed members into embeddable text (docs/design.md § Chunking and indexing).

- One chunk per `##` section; split further only past ~400 tokens.
- One synthesized "facts" chunk per member, rendered from frontmatter.
- Every chunk is prefixed with the member's first name and nickname before
  embedding, so the vector carries who it's about.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from app.ingest.parser import Member

# No model-specific tokenizer is wired in yet (ADR-0001: embeddings model
# still to be picked from the shortlist), so token count is approximated
# as ~4 characters/token — good enough to decide "does this section need
# splitting", not used for anything billed.
_CHARS_PER_TOKEN = 4
_MAX_TOKENS = 400
_MAX_CHARS = _MAX_TOKENS * _CHARS_PER_TOKEN


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # stable id, e.g. "joao-stories" or "joao-stories-2"
    text: str  # name-prefixed text, ready to embed
    member: str  # member id
    section: str  # section slug, or "facts" for the synthesized chunk
    source_file: str


def render_facts(member: Member) -> str:
    """Turn frontmatter into one short prose paragraph.

    Fields absent from the frontmatter are omitted entirely rather than
    guessed at, so retrieval correctly has nothing to offer for them (see
    the `unanswerable` eval category for members with a missing field).
    """
    m = member.meta
    first_name = str(m.get("name", member.id)).split()[0]

    work_bits = []
    if "job" in m:
        work_bits.append(f"works as a {m['job']}")
    if "city" in m:
        work_bits.append(f"lives in {m['city']}")
    sentences = [f"{first_name} {' and '.join(work_bits)}." if work_bits else f"{first_name}."]

    if "birthday" in m:
        sentences.append(f"Born {m['birthday']}.")
    if "diet" in m:
        sentences.append(f"Diet: {m['diet']}.")
    if "height_cm" in m:
        sentences.append(f"Height: {m['height_cm']}cm.")
    if "pets" in m:
        pets = m["pets"] or []
        sentences.append("No pets." if not pets else f"Pets: {', '.join(pets)}.")

    return " ".join(sentences)


def _split_long_section(body: str, max_chars: int = _MAX_CHARS) -> list[str]:
    """Split a section into char-budgeted parts on paragraph boundaries."""
    if len(body) <= max_chars:
        return [body]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        if current and current_len + len(para) + 2 > max_chars:
            parts.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        parts.append("\n\n".join(current))
    return parts or [body]


def _prefix(member: Member, label: str, text: str) -> str:
    first_name = str(member.meta.get("name", member.id)).split()[0]
    nickname = member.meta.get("nickname")
    who = f"{first_name} ({nickname})" if nickname else first_name
    return f"{who} – {label}: {text}"


def chunk_member(member: Member) -> list[Chunk]:
    chunks = [
        Chunk(
            id=f"{member.id}-facts",
            text=_prefix(member, "Facts", render_facts(member)),
            member=member.id,
            section="facts",
            source_file=member.source_file,
        )
    ]

    for section in member.sections:
        parts = _split_long_section(section.body)
        for i, part in enumerate(parts):
            suffix = "" if i == 0 else f"-{i + 1}"
            chunks.append(
                Chunk(
                    id=f"{member.id}-{section.slug}{suffix}",
                    text=_prefix(member, section.heading, part),
                    member=member.id,
                    section=section.slug,
                    source_file=member.source_file,
                )
            )

    return chunks


def chunk_members(members: list[Member]) -> list[Chunk]:
    return [chunk for member in members for chunk in chunk_member(member)]
