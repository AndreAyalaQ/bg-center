from pathlib import Path

from app.ingest.chunker import chunk_member, chunk_members, render_facts
from app.ingest.parser import load_members, parse_member

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "members"


def test_render_facts_includes_present_fields() -> None:
    joao = parse_member(SAMPLE_DIR / "joao.md")
    facts = render_facts(joao)
    assert "physiotherapist" in facts
    assert "Lisboa" in facts
    assert "1993-07-22" in facts
    assert "omnivore" in facts
    assert "178cm" in facts
    assert "dog: Bolacha" in facts


def test_render_facts_states_no_pets_when_field_is_an_empty_list() -> None:
    tomas = parse_member(SAMPLE_DIR / "tomas.md")
    assert "No pets." in render_facts(tomas)


def test_render_facts_omits_pets_entirely_when_field_is_absent() -> None:
    # Diogo has no `pets` field at all — this is a deliberate eval trap:
    # the bot should decline rather than guess, so the facts chunk must
    # not assert anything about pets either way.
    diogo = parse_member(SAMPLE_DIR / "diogo.md")
    facts = render_facts(diogo)
    assert "pet" not in facts.lower()


def test_chunk_member_produces_one_facts_chunk_plus_one_per_section() -> None:
    joao = parse_member(SAMPLE_DIR / "joao.md")
    chunks = chunk_member(joao)
    expected_sections = ["facts", "personality", "stories", "inside_jokes", "fun_facts"]
    assert [c.section for c in chunks] == expected_sections
    assert all(c.member == "joao" for c in chunks)
    assert all(c.source_file == "joao.md" for c in chunks)


def test_chunk_text_is_prefixed_with_name_and_nickname() -> None:
    joao = parse_member(SAMPLE_DIR / "joao.md")
    stories_chunk = next(c for c in chunk_member(joao) if c.section == "stories")
    assert stories_chunk.text.startswith("João (Jota) – Histórias:")


def test_chunk_ids_are_unique_across_the_whole_sample_group() -> None:
    members = load_members(SAMPLE_DIR)
    chunks = chunk_members(members)
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
    assert len(chunks) > len(members)  # at least the facts chunk + 1 section each
