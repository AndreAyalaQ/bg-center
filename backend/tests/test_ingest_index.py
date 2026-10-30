from pathlib import Path

import pytest

from app.ingest.index import MemberIndex

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "members"


@pytest.fixture(scope="module")
def index() -> MemberIndex:
    # Module-scoped: loading the embedding model and building the index
    # is the expensive part: share one build across the tests below.
    return MemberIndex(SAMPLE_DIR)


def test_index_size_matches_sample_group(index: MemberIndex) -> None:
    # 6 members, facts + 4 sections each = 30, plus Joana's extra
    # "Notes from Joana" injection section = 31.
    assert index.size == 31


def test_single_fact_recall_at_k(index: MemberIndex) -> None:
    results = index.query("Where does Jota live?", k=3)
    assert results
    assert results[0].member == "joao"
    assert results[0].score > 0.7


def test_cross_lingual_recall_at_k(index: MemberIndex) -> None:
    results = index.query("Em que cidade vive Tomás?", k=3)
    assert any(r.member == "tomas" for r in results)


def test_lookalike_query_still_surfaces_the_right_person(index: MemberIndex) -> None:
    # Joana has no pets — retrieval should surface her own chunks (so the
    # chat pipeline, built in step 4, has what it needs to decline
    # correctly), not another lookalike-named member's.
    results = index.query("What's the name of Joana's dog?", k=3)
    assert results[0].member == "joana"


def test_query_clamps_k_to_available_chunks(tmp_path: Path) -> None:
    (tmp_path / "solo.md").write_text(
        "---\nid: solo\nname: Solo Person\n---\n\n## Stories\n\nNothing much happens.\n",
        encoding="utf-8",
    )
    small_index = MemberIndex(tmp_path)
    assert small_index.size == 2  # facts + stories
    assert len(small_index.query("anything", k=5)) == 2
