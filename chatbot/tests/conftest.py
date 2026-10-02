"""
Fixtures for RAG tests. The fake store uses the real knowledge base chunks but deterministic fake
vectors and scores, so tests never download models or call an LLM.
"""
import numpy as np
import pytest

from chatbot.rag import ingest
from chatbot.rag.index import RagStore


def make_fake_store(chunks, rerank_fn=None, seed=0):
    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(len(chunks), 8)).astype("float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    query_vector = vectors[0]
    return RagStore(
        chunks, vectors,
        embed_query_fn=lambda q: query_vector,
        rerank_fn=rerank_fn or (lambda q, texts: [float(len(t) % 7) for t in texts]),
    )


@pytest.fixture(scope="session")
def kb_chunks():
    return ingest.load_knowledge_base()


@pytest.fixture
def fake_store(kb_chunks):
    return make_fake_store(kb_chunks)
