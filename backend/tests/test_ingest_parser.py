from pathlib import Path

import pytest

from app.ingest.parser import load_members, parse_member, slugify_section

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "members"


def test_slugify_section_collapses_pt_and_en_headings() -> None:
    assert slugify_section("Stories") == "stories"
    assert slugify_section("Histórias") == "stories"
    assert slugify_section("Piadas internas") == "inside_jokes"
    assert slugify_section("Inside jokes") == "inside_jokes"


def test_slugify_section_falls_back_for_unknown_headings() -> None:
    assert slugify_section("Notes from Joana") == "notes_from_joana"


def test_parse_member_reads_frontmatter_and_sections() -> None:
    member = parse_member(SAMPLE_DIR / "joao.md")
    assert member.id == "joao"
    assert member.meta["nickname"] == "Jota"
    assert member.meta["city"] == "Lisboa"
    assert "pets" in member.meta
    expected_slugs = ["personality", "stories", "inside_jokes", "fun_facts"]
    assert [s.slug for s in member.sections] == expected_slugs


def test_parse_member_missing_field_stays_absent() -> None:
    # Diogo's missing `pets` field is a deliberate eval trap (unanswerable
    # category) — the parser must not invent a default for it.
    member = parse_member(SAMPLE_DIR / "diogo.md")
    assert "pets" not in member.meta


def test_parse_member_rejects_file_without_frontmatter(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("# No frontmatter here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_member(bad)


def test_parse_member_rejects_wrong_typed_fields(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text(
        "---\nid: bad\nname: Bad Example\nheight_cm: not-a-number\n---\n\n## Stories\n\nHi.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid frontmatter"):
        parse_member(bad)


def test_parse_member_rejects_missing_name(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("---\nid: bad\n---\n\n## Stories\n\nHi.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid frontmatter"):
        parse_member(bad)


def test_parse_member_allows_unrecognized_extra_fields(tmp_path: Path) -> None:
    # extra="allow" on MemberFrontmatter: ad hoc fields like avatar_url or
    # tagline shouldn't need a schema change here to be accepted.
    ok = tmp_path / "ok.md"
    ok.write_text(
        "---\nid: ok\nname: Ok Example\navatar_url: https://example.com/a.png\n---\n\n"
        "## Stories\n\nHi.\n",
        encoding="utf-8",
    )
    member = parse_member(ok)
    assert member.meta["avatar_url"] == "https://example.com/a.png"


def test_load_members_reads_the_whole_sample_group() -> None:
    members = load_members(SAMPLE_DIR)
    assert {m.id for m in members} == {"joao", "joana", "rita", "tomas", "ines", "diogo"}


def test_load_members_raises_on_empty_dir(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        load_members(tmp_path)
