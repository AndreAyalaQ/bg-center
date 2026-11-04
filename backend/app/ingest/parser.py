"""Parse member Markdown files into frontmatter facts + free-text sections.

One member = one file: YAML frontmatter for structured facts, `##` sections
for free text (ADR-0004, docs/design.md § Data model).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

# PT and EN headings used across the sample docs collapse to the same
# language-independent slug, so `expected_section` in the eval cases
# doesn't need to vary by doc language.
_CANONICAL_SECTIONS = {
    "personalidade": "personality",
    "personality": "personality",
    "historias": "stories",
    "stories": "stories",
    "piadas internas": "inside_jokes",
    "inside jokes": "inside_jokes",
    "curiosidades": "fun_facts",
    "fun facts": "fun_facts",
}

_HEADING_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def slugify_section(heading: str) -> str:
    """Normalize a '##' heading (PT or EN) to a stable, language-independent slug."""
    ascii_heading = unicodedata.normalize("NFKD", heading).encode("ascii", "ignore").decode("ascii")
    normalized = ascii_heading.lower().strip()
    if normalized in _CANONICAL_SECTIONS:
        return _CANONICAL_SECTIONS[normalized]
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return slug or "section"


class Section(BaseModel):
    model_config = ConfigDict(frozen=True)

    heading: str  # heading text as written in the doc
    slug: str  # language-independent identifier, e.g. "stories"
    body: str  # section text with the heading line removed


class Member(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    meta: dict[str, Any]  # full YAML frontmatter
    sections: list[Section]
    source_file: str  # filename, e.g. "joao.md"


def parse_member(path: Path) -> Member:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name}: missing frontmatter")
    _, raw_front, body = text.split("---", 2)

    meta = yaml.safe_load(raw_front)
    if not isinstance(meta, dict) or "id" not in meta:
        raise ValueError(f"{path.name}: frontmatter missing 'id'")

    headings = list(_HEADING_RE.finditer(body))
    sections = []
    for i, match in enumerate(headings):
        heading = match.group(1).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        section_body = body[start:end].strip()
        if section_body:
            section = Section(heading=heading, slug=slugify_section(heading), body=section_body)
            sections.append(section)

    return Member(id=meta["id"], meta=meta, sections=sections, source_file=path.name)


def load_members(data_dir: Path) -> list[Member]:
    members = [parse_member(p) for p in sorted(data_dir.glob("*.md"))]
    if not members:
        raise SystemExit(f"No member files found in {data_dir}")
    return members
