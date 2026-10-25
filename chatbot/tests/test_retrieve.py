import pytest

from chatbot.rag import pipeline
from chatbot.rag.retrieve import MAX_FAQ_CHUNKS, cap_faq, filter_by_year, hybrid_search, rrf_fuse
from chatbot.tests.conftest import make_fake_store


def test_rrf_toy_example():
    # a: 1/61 + 1/62, c: 1/63 + 1/61, b: 1/62, d: 1/63
    fused = rrf_fuse([["a", "b", "c"], ["c", "a", "d"]], k=60)
    assert [item for item, _ in fused] == ["a", "c", "b", "d"]
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_item_in_one_list_only():
    fused = dict(rrf_fuse([["x"], []], k=60))
    assert fused == {"x": pytest.approx(1 / 61)}


def test_cap_faq_backfills_with_non_faq(fake_store):
    faq = [p for p, c in enumerate(fake_store.chunks) if c["is_faq"]]
    non_faq = [p for p, c in enumerate(fake_store.chunks) if not c["is_faq"]]
    picked = cap_faq(faq[:6] + non_faq[:6], fake_store)
    assert len(picked) == 5
    assert sum(fake_store.chunks[p]["is_faq"] for p in picked) == MAX_FAQ_CHUNKS
    assert picked[2:] == non_faq[:3]


@pytest.mark.parametrize("use_reranker", [True, False])
def test_final_context_never_has_more_than_two_faq_chunks(kb_chunks, use_reranker):
    # Reranker that prefers FAQ chunks, to push as many as possible into the top 5
    store = make_fake_store(kb_chunks, rerank_fn=lambda q, texts: [
        10.0 if t.rstrip().split("\n", 1)[0].endswith("?") else 1.0 for t in texts
    ])
    for query in ("what do you do", "u used agents?", "where did you study", "teaching"):
        results, _ = hybrid_search(store, query, use_reranker=use_reranker)
        assert len(results) == 5
        faq_count = sum(store.chunks[r["pos"]]["is_faq"] for r in results)
        assert faq_count <= MAX_FAQ_CHUNKS


def test_list_intent_returns_every_project_chunk(fake_store):
    route = {"standalone_question": "List Saravana's projects", "intent": "list", "type_filter": "project", "year": None}
    results, _, fallback = pipeline.retrieve(route, fake_store)
    expected = {c["chunk_id"] for c in fake_store.chunks if c["type"] == "project" and not c["is_faq"]}
    assert {r["chunk_id"] for r in results} == expected
    assert not fallback
    years = [fake_store.chunks[r["pos"]]["start_year"] for r in results]
    known = [y for y in years if y is not None]
    assert known == sorted(known, reverse=True), "newest first"
    assert years[len(known):] == [None] * (len(years) - len(known)), "unknown years last"


def test_timeframe_2021_filter_includes_sctimst_and_2021_research(fake_store):
    ids = {fake_store.chunks[p]["chunk_id"] for p in filter_by_year(fake_store, 2021)}
    assert "experience#saravana-perumal-r-senior-research-fellow-in-biomedical-technology-at-sctimst-july-2019-to-november-2023" in ids
    research_2021 = [c["chunk_id"] for c in fake_store.chunks
                     if c["source_file"] == "projects.md" and c["start_year"] is not None
                     and c["start_year"] <= 2021 <= (c["end_year"] or c["start_year"])]
    assert len(research_2021) >= 3  # two 2021 papers + the 2020-2023 bioprinting project
    assert set(research_2021) <= ids
    # Nothing outside 2021
    for p in filter_by_year(fake_store, 2021):
        c = fake_store.chunks[p]
        assert c["start_year"] <= 2021 <= (c["end_year"] if c["end_year"] is not None else c["start_year"])


def test_timeframe_lookup_only_uses_chunks_from_that_year(fake_store):
    route = {"standalone_question": "What was Saravana doing in 2021?", "intent": "timeframe",
             "type_filter": None, "year": 2021}
    allowed = {fake_store.chunks[p]["chunk_id"] for p in filter_by_year(fake_store, 2021)}
    results, _, _ = pipeline.retrieve(route, fake_store, use_reranker=False)
    assert results
    assert {r["chunk_id"] for r in results} <= allowed


@pytest.mark.parametrize("intent", ["out_of_scope", "chitchat"])
def test_no_retrieval_for_out_of_scope_and_chitchat(kb_chunks, intent):
    store = make_fake_store(kb_chunks, rerank_fn=lambda q, texts: [pipeline.ROUTE_RESCUE_SCORE - 1] * len(texts))
    route = {"standalone_question": "Who will win the election?", "intent": intent, "type_filter": None, "year": None}
    assert pipeline.retrieve(route, store, use_reranker=True) == ([], None, False)
    assert pipeline.retrieve(dict(route), store, use_reranker=False) == ([], None, False)


def test_confident_match_rescues_a_misrouted_question(kb_chunks):
    store = make_fake_store(kb_chunks, rerank_fn=lambda q, texts: [pipeline.ROUTE_RESCUE_SCORE + 3] * len(texts))
    route = {"standalone_question": "Where is Saravana based?", "intent": "out_of_scope", "type_filter": None, "year": None}
    results, top_score, fallback = pipeline.retrieve(route, store, use_reranker=True)
    assert len(results) == 5 and not fallback
    assert route["intent"] == "lookup" and route["rerouted_from"] == "out_of_scope"


def test_reranker_sees_at_most_the_candidate_cap_with_long_passages_cut(kb_chunks):
    from chatbot.rag import retrieve as retrieve_module
    seen = []
    store = make_fake_store(kb_chunks, rerank_fn=lambda q, texts: seen.extend(texts) or [0.0] * len(texts))
    hybrid_search(store, "rag projects", use_reranker=True)
    assert len(seen) == retrieve_module.RERANK_CANDIDATES
    assert all(len(t.split()) <= retrieve_module.RERANK_MAX_WORDS for t in seen)
    seen.clear()
    hybrid_search(store, "rag projects", use_reranker=True, rerank_candidates=3)
    assert len(seen) == 3
