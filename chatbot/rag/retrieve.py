"""
Retrieval over a RagStore: hybrid dense + BM25 with Reciprocal Rank Fusion, optional cross-encoder
rerank, FAQ cap, and in-Python type / year filtering (the corpus is ~200 chunks, so every chunk is
scored and then filtered). A website chunk and the knowledge-base chunk it duplicates (`same_as`) count
as one record: results and lists keep only one of the two.
"""
import os
import re
import time

import numpy as np

CANDIDATES_PER_RETRIEVER = 20
# Only the fused top N go to the cross-encoder. It is the slowest CPU step (~25-100 ms a pair on one thread,
# several times that on Render's free CPU) and its cost is linear in N: 20 -> 10 halved it with the same
# hit@5 (0.975), and 10 -> 6 cut another ~35%.
RERANK_CANDIDATES = int(os.getenv("RAG_RERANK_CANDIDATES", "6"))
# Passages are cut to this many words for the cross-encoder only (cost grows with length; the heading and
# first paragraph carry the match). Median chunk is ~40 words, so this only shortens the long ones (~13% faster).
RERANK_MAX_WORDS = 100
RRF_K = 60
FINAL_K = 5
MAX_FAQ_CHUNKS = 2


def rrf_fuse(rankings, k=RRF_K):
    """Reciprocal Rank Fusion. `rankings` are lists of ids, best first. Returns [(id, score)] best first."""
    scores = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], str(kv[0])))


def record_key(chunk):
    return chunk.get("same_as") or chunk["chunk_id"]


def cap_faq(positions, store, limit=FINAL_K, max_faq=MAX_FAQ_CHUNKS):
    """
    Take the first `limit` positions, allowing at most `max_faq` FAQ chunks and one chunk per record;
    backfill with the next ones.
    """
    picked, faq_count, records = [], 0, set()
    for pos in positions:
        key = record_key(store.chunks[pos])
        if key in records:
            continue
        records.add(key)
        if store.chunks[pos]["is_faq"]:
            if faq_count >= max_faq:
                continue
            faq_count += 1
        picked.append(pos)
        if len(picked) == limit:
            break
    return picked


def filter_by_year(store, year):
    """Positions of chunks active in `year`. Unknown start year -> excluded; unknown end -> start year only."""
    positions = []
    for pos, c in enumerate(store.chunks):
        start, end = c.get("start_year"), c.get("end_year")
        if start is None:
            continue
        if start <= year <= (end if end is not None else start):
            positions.append(pos)
    return positions


def first_sentence(text):
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    body = " ".join(body.split())
    match = re.match(r"(.+?[.!?])(\s|$)", body)
    return match.group(1) if match else body


def list_by_type(store, type_filter):
    """
    Every non-FAQ record of a type, newest first (unknown years last), as heading + first sentence. A
    record on the website is listed from its website chunk, the one visitors see, not its KB twin.
    """
    chunks = [(p, c) for p, c in enumerate(store.chunks) if c["type"] == type_filter and not c["is_faq"]]
    on_site = {c["same_as"] for _, c in chunks if c.get("same_as")}
    positions = [p for p, c in chunks if c["chunk_id"] not in on_site]
    positions.sort(key=lambda p: (store.chunks[p]["start_year"] is None, -(store.chunks[p]["start_year"] or 0),
                                  store.chunks[p]["chunk_id"]))
    results = []
    for pos in positions:
        c = store.chunks[pos]
        heading = c["display_text"].split("\n", 1)[0]
        results.append({"pos": pos, "chunk_id": c["chunk_id"], "score": None,
                        "text": f"{heading}\n{first_sentence(c['display_text'])}"})
    return results


def rerank_text(text):
    words = text.split()
    return text if len(words) <= RERANK_MAX_WORDS else " ".join(words[:RERANK_MAX_WORDS])


def hybrid_search(store, query, *, subset=None, use_reranker=True, timings=None, rerank_candidates=None):
    """
    Dense top 20 + BM25 top 20 fused with RRF, then (optionally) cross-encoder rerank of the fused
    top RERANK_CANDIDATES (or `rerank_candidates`), then the FAQ cap down to 5. Returns (results, top_score) where top_score is the best
    rerank score when reranking, else the best dense cosine among the candidates.
    """
    timings = timings if timings is not None else {}
    allowed = set(range(len(store))) if subset is None else set(subset)
    if not allowed:
        return [], None

    t = time.perf_counter()
    dense = store.dense_scores(store.embed_query(query))
    bm25 = store.bm25_scores(query)
    timings["embed_search_ms"] = round((time.perf_counter() - t) * 1000, 1)

    order = [p for p in np.argsort(-dense, kind="stable") if p in allowed]
    dense_top = order[:CANDIDATES_PER_RETRIEVER]
    bm25_order = [p for p in np.argsort(-bm25, kind="stable") if p in allowed and bm25[p] > 0]
    bm25_top = bm25_order[:CANDIDATES_PER_RETRIEVER]
    fused = rrf_fuse([dense_top, bm25_top])[:CANDIDATES_PER_RETRIEVER]
    candidates = [int(p) for p, _ in fused]
    rrf_score = {int(p): s for p, s in fused}

    rerank = {}
    if use_reranker and candidates:
        candidates = candidates[:rerank_candidates or RERANK_CANDIDATES]
        t = time.perf_counter()
        scores = store.rerank_fn(query, [rerank_text(store.chunks[p]["display_text"]) for p in candidates])
        rerank = dict(zip(candidates, scores))
        candidates.sort(key=lambda p: -rerank[p])
        timings["rerank_ms"] = round((time.perf_counter() - t) * 1000, 1)

    final = cap_faq(candidates, store)
    results = [{
        "pos": p,
        "chunk_id": store.chunks[p]["chunk_id"],
        "score": round(float(rerank[p] if rerank else rrf_score[p]), 4),
        "dense": round(float(dense[p]), 4),
        "text": store.chunks[p]["display_text"],
    } for p in final]

    if not candidates:
        top_score = None
    elif rerank:
        top_score = float(max(rerank.values()))
    else:
        top_score = float(max(dense[p] for p in candidates))
    return results, top_score
