from django.core.management.base import BaseCommand, CommandError

from chatbot.rag import index as rag_index
from chatbot.rag.ingest import KnowledgeBaseError


class Command(BaseCommand):
    help = ("Builds the chatbot's FAISS index from knowledge_base/, GitHub repos (RAG_INCLUDE_GITHUB) and "
            "ContextSnippet rows. Skips the build when faiss_index/manifest.json already matches.")

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Rebuild even if the manifest matches.")

    def handle(self, *args, force=False, **options):
        try:
            chunks = rag_index.local_chunks()
        except KnowledgeBaseError as e:
            raise CommandError(f"Knowledge base is invalid: {e}")

        if rag_index.include_github():
            github = rag_index.fetch_github_chunks()
            if github is None:
                github = rag_index.saved_github_chunks()
                self.stdout.write(self.style.WARNING(
                    f"GitHub unreachable; reusing {len(github)} GitHub chunk(s) from the existing index."))
            chunks += github

        old = rag_index.read_manifest()
        new = rag_index.build_manifest(chunks)
        diff = rag_index.diff_manifest(old, new)
        files_present = all((rag_index.INDEX_DIR / f).exists() for f in ("index.faiss", "chunks.json"))
        same_model = (old or {}).get("embedding_model") == new["embedding_model"]
        unchanged = files_present and same_model and not (diff["added"] or diff["changed"] or diff["removed"])

        self._download_models()

        counts = ", ".join(f"{k} {len(v)}" for k, v in diff.items())
        if unchanged and not force:
            self.stdout.write(self.style.SUCCESS(f"unchanged ({counts})"))
            return

        if old and not same_model:
            self.stdout.write(f"Embedding model changed: {old.get('embedding_model')} -> {new['embedding_model']}")
        self.stdout.write(f"Building index for {len(chunks)} chunks ({counts})...")
        store = rag_index.build_store(chunks)
        rag_index.save_index(store)
        self.stdout.write(self.style.SUCCESS(
            f"Built {rag_index.INDEX_DIR / 'index.faiss'}: {len(store)} chunks; {counts}"))

    def _download_models(self):
        """Make sure the ONNX models are in .model_cache/ so the first chat request after a deploy doesn't
        download them (the reranker alone took ~90s to fetch in testing)."""
        rag_index.get_embedder()
        if rag_index.reranker_enabled():
            rag_index.get_reranker()
        self.stdout.write(f"Models ready in {rag_index.MODEL_CACHE_DIR} "
                          f"(process RSS {rag_index.process_rss_mb()} MB)")
