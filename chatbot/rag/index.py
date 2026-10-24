"""
FAISS + BM25 index over the knowledge base and website chunks, with a manifest so a stale index is never
served. Website content changes through the admin, so a running process re-checks it every
SITE_RECHECK_SECONDS (and right after an admin save) and re-embeds only the chunks that changed.

Files in faiss_index/:
    index.faiss    dense vectors (inner product over normalized embeddings = cosine)
    chunks.json    chunk text + metadata, row i matches vector i
    manifest.json  {"embedding_model": ..., "chunks": {chunk_id: content_hash}}

Models run on ONNX via fastembed (no PyTorch) so the whole process fits Render's free 512MB.
"""
import collections
import datetime
import json
import logging
import os
import threading
import time
from pathlib import Path

import numpy as np
from django.conf import settings

from chatbot.rag import ingest, site_content

logger = logging.getLogger(__name__)

INDEX_DIR = Path(settings.BASE_DIR) / "faiss_index"
# Inside the project so models downloaded during the Render build are still there at runtime
MODEL_CACHE_DIR = Path(settings.BASE_DIR) / ".model_cache"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
EMBED_BATCH_SIZE = 4
# Attention buffers scale with batch x 512^2: batch 20 spiked to ~640MB RSS, batch 2 stays at ~365MB
RERANK_BATCH_SIZE = 2
# ONNX's CPU arena never returns memory and grows with every new input shape (hit 1GB in testing)
ONNX_OPTIONS = {"threads": 1, "enable_cpu_mem_arena": False}
# How often a serving process compares its index to the knowledge base + website content (~25 queries)
SITE_RECHECK_SECONDS = 60


def env_flag(name, default=True):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def include_github():
    return env_flag("RAG_INCLUDE_GITHUB", True)


def reranker_enabled():
    return env_flag("RAG_RERANKER", True)


# ─── Models (loaded lazily, once per process) ────────────────────────

def process_rss_mb():
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / 2**20, 1)
    except ImportError:
        try:
            import resource  # Linux: ru_maxrss is the peak, in KB
            return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        except ImportError:
            return None


def log_memory(event):
    logger.info("RAG memory: %s, process RSS %s MB", event, process_rss_mb())


_model_lock = threading.Lock()
_embedder = None
_reranker = None


def get_embedder():
    global _embedder
    with _model_lock:
        if _embedder is None:
            from fastembed import TextEmbedding
            _embedder = TextEmbedding(EMBEDDING_MODEL, cache_dir=str(MODEL_CACHE_DIR), **ONNX_OPTIONS)
            log_memory(f"embedding model {EMBEDDING_MODEL} loaded")
    return _embedder


def get_reranker():
    global _reranker
    with _model_lock:
        if _reranker is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            _reranker = TextCrossEncoder(RERANKER_MODEL, cache_dir=str(MODEL_CACHE_DIR), **ONNX_OPTIONS)
            log_memory(f"reranker {RERANKER_MODEL} loaded")
    return _reranker


def _normalize(vectors):
    vectors = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def embed_documents(texts):
    if not texts:
        return np.zeros((0, 384), dtype="float32")
    return _normalize(list(get_embedder().embed(texts, batch_size=EMBED_BATCH_SIZE)))


def embed_query(text):
    return _normalize(list(get_embedder().embed([QUERY_PREFIX + text])))[0]


def rerank_scores(query, texts):
    return [float(s) for s in get_reranker().rerank(query, texts, batch_size=RERANK_BATCH_SIZE)]


# ─── Store ───────────────────────────────────────────────────────────

class RagStore:
    """Chunks + FAISS index + BM25. Embedding/rerank functions are injectable for tests."""

    def __init__(self, chunks, vectors, *, embed_query_fn=embed_query, rerank_fn=rerank_scores,
                 embedding_model=EMBEDDING_MODEL):
        import faiss
        from rank_bm25 import BM25Okapi

        self.chunks = list(chunks)
        self.vectors = np.asarray(vectors, dtype="float32").reshape(len(self.chunks), -1)
        self.embedding_model = embedding_model
        self.embed_query = embed_query_fn
        self.rerank_fn = rerank_fn
        self.faiss_index = faiss.IndexFlatIP(self.vectors.shape[1] if len(self.chunks) else 384)
        if len(self.chunks):
            self.faiss_index.add(self.vectors)
        self.bm25 = BM25Okapi([ingest.tokenize(c["bm25_text"]) or ["_"] for c in self.chunks]) if self.chunks else None
        self.lock = threading.Lock()

    def __len__(self):
        return len(self.chunks)

    def dense_scores(self, query_vector):
        """Cosine similarity of the query against every chunk (corpus is tiny, so search all of it)."""
        scores = np.zeros(len(self.chunks), dtype="float32")
        if not len(self.chunks):
            return scores
        sims, ids = self.faiss_index.search(np.asarray([query_vector], dtype="float32"), len(self.chunks))
        scores[ids[0]] = sims[0]
        return scores

    def bm25_scores(self, query):
        if self.bm25 is None:
            return np.zeros(0)
        tokens = ingest.tokenize(query)
        return np.asarray(self.bm25.get_scores(tokens)) if tokens else np.zeros(len(self.chunks))

    def manifest(self):
        return build_manifest(self.chunks, self.embedding_model)

    def add_chunk(self, chunk, vector):
        with self.lock:
            self.chunks.append(chunk)
            self.vectors = np.vstack([self.vectors, np.asarray([vector], dtype="float32")])
            self.faiss_index.add(np.asarray([vector], dtype="float32"))
            from rank_bm25 import BM25Okapi
            self.bm25 = BM25Okapi([ingest.tokenize(c["bm25_text"]) or ["_"] for c in self.chunks])


# ─── Manifest ────────────────────────────────────────────────────────

def build_manifest(chunks, embedding_model=EMBEDDING_MODEL):
    return {
        "embedding_model": embedding_model,
        "chunks": {c["chunk_id"]: c["content_hash"] for c in chunks},
    }


def diff_manifest(old, new):
    """Per-category chunk_id lists between two manifests' chunk maps."""
    old_chunks, new_chunks = (old or {}).get("chunks", {}), new.get("chunks", {})
    return {
        "added": sorted(set(new_chunks) - set(old_chunks)),
        "removed": sorted(set(old_chunks) - set(new_chunks)),
        "changed": sorted(k for k in set(old_chunks) & set(new_chunks) if old_chunks[k] != new_chunks[k]),
        "unchanged": sorted(k for k in set(old_chunks) & set(new_chunks) if old_chunks[k] == new_chunks[k]),
    }


def local_chunks(kb_dir=ingest.KB_DIR):
    """Chunks whose source lives with the app: knowledge base files, website content, ContextSnippet rows."""
    kb = ingest.load_knowledge_base(kb_dir)
    site = site_content.link_duplicates(site_content.site_chunks(), kb)
    return kb + site + ingest.snippet_chunks(ingest.load_snippets())


def check_freshness(manifest, kb_dir=ingest.KB_DIR, with_github=None):
    """
    Compare a saved manifest to the current knowledge base, snippets, and model, without any network
    call (GitHub chunks are taken as they were at build time). Returns (is_fresh, reasons).
    """
    with_github = include_github() if with_github is None else with_github
    if not manifest:
        return False, ["no manifest"]
    reasons = []
    if manifest.get("embedding_model") != EMBEDDING_MODEL:
        reasons.append(f"embedding model changed ({manifest.get('embedding_model')} -> {EMBEDDING_MODEL})")
    saved = manifest.get("chunks", {})
    saved_local = {k: v for k, v in saved.items() if not k.startswith("github#")}
    diff = diff_manifest({"chunks": saved_local}, build_manifest(local_chunks(kb_dir)))
    for key in ("added", "changed", "removed"):
        if diff[key]:
            reasons.append(f"{len(diff[key])} chunk(s) {key}: {', '.join(diff[key][:3])}")
    if not with_github and any(k.startswith("github#") for k in saved):
        reasons.append("RAG_INCLUDE_GITHUB is off but the index has GitHub chunks")
    return not reasons, reasons


# ─── Persistence ─────────────────────────────────────────────────────

def save_index(store, index_dir=INDEX_DIR):
    import faiss
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(store.faiss_index, str(index_dir / "index.faiss"))
    (index_dir / "chunks.json").write_text(json.dumps(store.chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest = store.manifest() | {"built_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (index_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    # Remove the old LangChain pickle docstore if it is still around
    (index_dir / "index.pkl").unlink(missing_ok=True)


def read_manifest(index_dir=INDEX_DIR):
    try:
        return json.loads((Path(index_dir) / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_saved_index(index_dir=INDEX_DIR):
    import faiss
    index_dir = Path(index_dir)
    chunks = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
    faiss_index = faiss.read_index(str(index_dir / "index.faiss"))
    vectors = faiss_index.reconstruct_n(0, faiss_index.ntotal) if faiss_index.ntotal else np.zeros((0, 384), "float32")
    return RagStore(chunks, vectors)


def load_reusable_index(index_dir=INDEX_DIR):
    """The saved index, for reusing its vectors, or None if it can't be read or used a different model."""
    if (read_manifest(index_dir) or {}).get("embedding_model") != EMBEDDING_MODEL:
        return None
    try:
        return load_saved_index(index_dir)
    except Exception:
        return None


def saved_github_chunks(index_dir=INDEX_DIR):
    try:
        chunks = json.loads((Path(index_dir) / "chunks.json").read_text(encoding="utf-8"))
        return [c for c in chunks if c["type"] == "github"]
    except (OSError, ValueError):
        return []


def fetch_github_chunks():
    from chatbot.github_connector import fetch_github_repos
    username = os.getenv("GITHUB_USERNAME", "saravanagithub14")
    repos = fetch_github_repos(username)
    if repos is None:
        return None
    return ingest.github_chunks(repos)


def build_store(chunks, reuse=None):
    """Embed `chunks`, reusing vectors from the store `reuse` for chunks whose content hash is unchanged."""
    known = {}
    if reuse is not None:
        known = {(c["chunk_id"], c["content_hash"]): reuse.vectors[i] for i, c in enumerate(reuse.chunks)}
    missing = [c for c in chunks if (c["chunk_id"], c["content_hash"]) not in known]
    fresh = dict(zip((c["chunk_id"] for c in missing), embed_documents([c["embed_text"] for c in missing])))
    vectors = [known.get((c["chunk_id"], c["content_hash"]), fresh.get(c["chunk_id"])) for c in chunks]
    return RagStore(chunks, np.asarray(vectors, dtype="float32").reshape(len(chunks), -1))


# ─── Process-wide store ──────────────────────────────────────────────

_store = None
_store_lock = threading.Lock()
_checked_at = 0.0


def get_store():
    """Load the saved index, rebuilding in-process if it is missing or stale."""
    global _store, _checked_at
    if _store is not None:
        if time.monotonic() - _checked_at >= SITE_RECHECK_SECONDS:
            refresh_store()
        return _store
    with _store_lock:
        if _store is None:
            _store = _load_or_rebuild()
            _checked_at = time.monotonic()
    return _store


def site_changed(**kwargs):
    """Signal receiver for portfolio model saves/deletes: re-check the index on the next chat."""
    global _checked_at
    _checked_at = 0.0


def refresh_store():
    """
    Swap in a new store if the knowledge base or website content changed since it was built. Only the
    changed chunks are embedded; GitHub chunks are kept as they are. Never raises: on any error the
    current store keeps serving and the check is retried after SITE_RECHECK_SECONDS.
    """
    global _store, _checked_at
    with _store_lock:
        _checked_at = time.monotonic()
        try:
            current = _store
            local = local_chunks()
            old = {c["chunk_id"]: c["content_hash"] for c in current.chunks if c["type"] != "github"}
            if old == {c["chunk_id"]: c["content_hash"] for c in local}:
                return
            github = [c for c in current.chunks if c["type"] == "github"]
            store = build_store(local + github, reuse=current)
            diff = diff_manifest(current.manifest(), store.manifest())
            logger.info("RAG index refreshed: %s", ", ".join(f"{k} {len(v)}" for k, v in diff.items()))
            _store = store
            save_index(store)
        except Exception as e:
            logger.warning("RAG index refresh failed; serving the current index: %s", e)


def warm_up():
    """Load the index and both ONNX models, so the first chat doesn't pay for it (~20s on Render)."""
    try:
        store = get_store()
        store.embed_query("warm up")
        if reranker_enabled():
            store.rerank_fn("warm up", ["warm up"])
        log_memory("RAG warm-up done")
    except Exception as e:  # the first chat will load them instead
        logger.warning("RAG warm-up failed: %s", e)


def reset_store():
    global _store, _checked_at
    _store, _checked_at = None, 0.0


def _load_or_rebuild(index_dir=INDEX_DIR):
    manifest = read_manifest(index_dir)
    files_present = all((Path(index_dir) / f).exists() for f in ("index.faiss", "chunks.json"))
    if manifest and files_present:
        fresh, reasons = check_freshness(manifest)
        if fresh:
            store = load_saved_index(index_dir)
            logger.info("Loaded RAG index: %d chunks", len(store))
            return store
        logger.warning("RAG index is stale (%s). Rebuilding in-process; run `manage.py build_rag_index` "
                       "to avoid this at startup.", "; ".join(reasons))
        github = saved_github_chunks(index_dir) if include_github() else []
        previous = load_reusable_index(index_dir)
    else:
        logger.warning("No RAG index found in %s. Building it in-process.", index_dir)
        github = (fetch_github_chunks() or []) if include_github() else []
        previous = None

    store = build_store(local_chunks() + github, reuse=previous)
    try:
        save_index(store, index_dir)
    except OSError as e:
        logger.warning("Could not save rebuilt RAG index: %s", e)
    return store


def add_snippet_to_live_index(snippet):
    """Append a ContextSnippet to the running index and persist it (manifest included)."""
    store = get_store()
    chunk = ingest.snippet_chunks([snippet])[0]
    store.add_chunk(chunk, embed_documents([chunk["embed_text"]])[0])
    save_index(store)
    return chunk


def status():
    store = get_store()
    manifest = read_manifest()
    try:
        fresh, reasons = check_freshness(manifest)
    except ingest.KnowledgeBaseError as e:
        fresh, reasons = False, [str(e)]
    return {
        "chunk_count": len(store),
        "chunks_by_type": dict(collections.Counter(c["type"] for c in store.chunks)),
        "faq_chunks": sum(1 for c in store.chunks if c["is_faq"]),
        "manifest_embedding_model": (manifest or {}).get("embedding_model"),
        "manifest_built_at": (manifest or {}).get("built_at"),
        "manifest_matches_knowledge_base": fresh,
        "stale_reasons": reasons,
        "bm25_ready": store.bm25 is not None,
        "reranker_enabled": reranker_enabled(),
        "reranker_loaded": _reranker is not None,
        "embedder_loaded": _embedder is not None,
        "process_rss_mb": process_rss_mb(),
    }
