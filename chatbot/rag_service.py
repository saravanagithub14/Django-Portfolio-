"""
Entry points for the chatbot's RAG layer. The implementation lives in chatbot/rag/:

    ingest.py    knowledge_base/*.md (+ GitHub repos, ContextSnippet rows) -> chunks
    index.py     FAISS + BM25 store, manifest, staleness check, ONNX models
    retrieve.py  hybrid search, RRF, rerank, FAQ cap, type/year filters
    pipeline.py  condense/route -> retrieve by intent -> fallback check -> generate
"""
from chatbot.rag.index import add_snippet_to_live_index, get_store, status  # noqa: F401
