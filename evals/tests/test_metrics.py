from app.ingest.index import RetrievedChunk
from evals.cases import GoldenCase
from evals.metrics import keyword_coverage, ndcg, reciprocal_rank


def _chunk(member: str, text: str = "") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{member}-facts",
        text=text,
        member=member,
        section="facts",
        source_file=f"{member}.md",
        score=0.9,
    )


def _case(**kwargs: object) -> GoldenCase:
    base: dict[str, object] = {"id": "t", "category": "single_fact", "question": "q?"}
    base.update(kwargs)
    return GoldenCase.model_validate(base)


# --- reciprocal_rank --------------------------------------------------------


def test_reciprocal_rank_is_one_when_first_result_matches() -> None:
    case = _case(expected_members=["joao"], must_contain=["Lisboa"])
    retrieved = [_chunk("joao"), _chunk("joana")]
    assert reciprocal_rank(retrieved, case) == 1.0


def test_reciprocal_rank_is_one_half_when_second_result_matches() -> None:
    case = _case(expected_members=["joana"], must_contain=["Porto"])
    retrieved = [_chunk("joao"), _chunk("joana")]
    assert reciprocal_rank(retrieved, case) == 0.5


def test_reciprocal_rank_is_zero_when_not_found() -> None:
    case = _case(expected_members=["tomas"], must_contain=["x"])
    retrieved = [_chunk("joao"), _chunk("joana")]
    assert reciprocal_rank(retrieved, case) == 0.0


def test_reciprocal_rank_is_none_without_expected_members() -> None:
    case = _case(expected_members=[], expect_decline=True)
    assert reciprocal_rank([_chunk("joao")], case) is None


# --- ndcg --------------------------------------------------------------


def test_ndcg_is_one_for_a_perfectly_ordered_result() -> None:
    case = _case(expected_members=["joao", "joana"], must_contain=["x"])
    retrieved = [_chunk("joao"), _chunk("joana"), _chunk("rita")]
    assert ndcg(retrieved, case) == 1.0


def test_ndcg_is_lower_when_relevant_results_rank_later() -> None:
    case = _case(expected_members=["rita"], must_contain=["x"])
    perfect = ndcg([_chunk("rita"), _chunk("joao")], case)
    worse = ndcg([_chunk("joao"), _chunk("rita")], case)
    assert worse is not None and perfect is not None
    assert worse < perfect


def test_ndcg_is_zero_for_no_relevant_results() -> None:
    case = _case(expected_members=["tomas"], must_contain=["x"])
    assert ndcg([_chunk("joao"), _chunk("joana")], case) == 0.0


def test_ndcg_is_none_without_expected_members() -> None:
    case = _case(expected_members=[], judge_rubric="r")
    assert ndcg([_chunk("joao")], case) is None


# --- keyword_coverage --------------------------------------------------------


def test_keyword_coverage_full_when_all_terms_present() -> None:
    case = _case(must_contain=["Lisboa", "physiotherapist"])
    retrieved = [_chunk("joao", "João works as a physiotherapist and lives in Lisboa.")]
    assert keyword_coverage(retrieved, case) == 1.0


def test_keyword_coverage_partial_when_some_terms_missing() -> None:
    case = _case(must_contain=["Lisboa", "nurse"])
    retrieved = [_chunk("joao", "João lives in Lisboa.")]
    assert keyword_coverage(retrieved, case) == 0.5


def test_keyword_coverage_is_accent_and_case_insensitive() -> None:
    case = _case(must_contain=["Inês"])
    retrieved = [_chunk("ines", "Lives with INES in Braga.")]
    assert keyword_coverage(retrieved, case) == 1.0


def test_keyword_coverage_must_contain_any_counts_as_one_unit() -> None:
    case = _case(must_contain_any=["Lisboa", "Lisbon"])
    retrieved = [_chunk("joao", "Lives in Lisbon.")]
    assert keyword_coverage(retrieved, case) == 1.0


def test_keyword_coverage_is_none_without_keywords() -> None:
    case = _case(expect_decline=True)
    assert keyword_coverage([_chunk("joao")], case) is None
