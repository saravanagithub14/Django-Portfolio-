# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Personal portfolio site for Saravana Perumal R. (Django 5, SQLite), with an AI chatbot (V.E.R.A., "Virtual Engine for Retrieval and Answers") that answers visitor questions about Saravana using RAG over the portfolio content. V.E.R.A. speaks as "I" but is his assistant: it refers to him as "Saravana"/"he" and never claims his work as its own. Its voice, fixed lines, logo and widget design come from the V.E.R.A. brand kit (kept outside the repo). Deployed on Render (`build.sh` is the build command; WhiteNoise serves static files).

## Commands

```bash
pip install -r requirements.txt               # requirements-dev.txt adds pytest, pytest-django, deepeval
python manage.py runserver                    # http://127.0.0.1:8000
python manage.py check
python manage.py makemigrations && python manage.py migrate
python manage.py build_rag_index              # (re)build faiss_index/ if the manifest is stale; --force to always rebuild
./build.sh                                    # Render build: install, collectstatic, migrate, build_rag_index

pytest                                        # chatbot/tests (no models or LLM calls; uses fake vectors)
pytest chatbot/tests/test_retrieve.py::test_rrf_toy_example
python chatbot/eval/run_eval.py               # golden-set eval: real models + LLM; DeepEval judge costs OpenAI calls
python chatbot/eval/run_eval.py --no-deepeval --limit 10
```

No linter/formatter is configured. To exercise the chatbot end to end:

```bash
curl -X POST http://127.0.0.1:8000/chatbot/api/chat/ -H "Content-Type: application/json" -d '{"message":"what projects have you built?"}'
curl http://127.0.0.1:8000/health             # index chunks by type, manifest freshness, BM25/reranker status, RSS
```

On Windows, set `PYTHONIOENCODING=utf-8` when printing model output from scripts; replies contain non-cp1252 characters.

## Architecture

Two Django apps under the `portfolio_hub` project:

### `portfolio/` — content pages
- **All site content lives in the database** (`db.sqlite3` is committed and is the source of truth), edited via Django admin. `portfolio/models.py` has ~35 models: a `UserProfile` plus a `*Page` model per page (`ExperiencePage`, `ProjectPage`, …) with child item models.
- Each view in `portfolio/views.py` queries the DB and **reshapes the rows into the nested dict structure the templates expect** (that structure originally came from JSON files). When changing a model or template, keep the view's dict shape in sync with the template.
- `portfolio/context_processors.py::portfolio_context` injects `config` (site title, social links, navigation, `chat_widget` settings) and `bio` into every template, and computes `active_page` from the URL path. The chat widget is only rendered (`templates/base.html`) when an enabled `Chatbot` row exists.
- Every page also has a legacy `*.html` URL alias (`portfolio/urls.py`) for links from the old static site.
- **The 3D graph is generated from the content models** (`portfolio/graph.py::build_graph`, called by `views.get_graph_data()` on every page): experience sections → jobs, featured + categorized projects, skill categories → skills, degrees/certifications, publications, workshops/seminars, focus cards, and contact fields. Admin edits therefore show up in the graph on the next page load. The old `GraphNode` table is no longer read or shown in admin. Top-level node ids equal each page's `active_page` (that drives the "You are here" highlight). End nodes have no link of their own; `graph.js` sends them to their nearest ancestor's page, resolved from the site root.
- **Admin:** `/admin/` (or `/login/`). Projects and Jobs also have flat list views, because featured projects have no category and so don't appear under Project Categories.
- **Graph backdrop:** every page that has `graph_data` (all of `base.html`'s pages and the landing page) includes `components/graph_background.html`. It's a fixed, faint, slowly orbiting graph behind the content (`#graph-container[data-mode=background]`, `pointer-events: none`, labels hidden, glows hidden in light mode), and the 3D libraries download only after the page's `load` event. `components/graph_section.html` at the bottom of pages is just an "Open the graph" button: any `[data-graph-explore]` element adds `html.graph-exploring`, which hides the content and calls `window.portfolioGraph.setExplore(true)` (interactive, labels, clickable nodes); Esc or "Back to page" exits. `graph.html` still renders the full-screen interactive graph (no `data-mode`). Styles: `static/css/graph_bg.css`.
- **Performance:** the graph builds with ~16 queries; keep it prefetch-based (per-node queries once cost ~120 queries/page). Headless browsers with software WebGL (swiftshader) render the backdrop very slowly; measure with the GPU path before concluding it's slow.
- Tests: `portfolio/tests/` (graph generation, admin edits → graph). The root `conftest.py` swaps in plain static storage, because tests render with `DEBUG=False`.
- **Theme:** all colours come from tokens in `static/css/theme.css` (dark default, light via `<html data-theme>` or the system setting). `components/theme_head.html` (included in `base.html`, `index.html`, `graph.html`) applies the saved choice before first paint; `static/js/theme.js` drives every `[data-theme-toggle]` button and fires a `themechange` event that the canvases and the graph listen to. Use `--primary` for lime text and `--primary-bg` + `--on-primary` for lime fills (in light mode `--primary` is dark green); decorative glows use `--glow`, which is transparent in light mode. The 3D graph and its overlays stay dark in both themes (`--graph-bg`). Don't add hard-coded colours.
- **Linking CSS/JS:** use `{% asset 'path' %}` (`portfolio_extras`), not `{% static %}`, for local CSS/JS. In DEBUG it appends `?v=<mtime>`, because browsers kept stale copies of edited files (once an old `chat_widget.js` ran against the new CSS). In production it's plain `static()`, with hashed names. `whitenoise.runserver_nostatic` also makes `runserver` send `max-age=0`.
- **Static files** use WhiteNoise's `CompressedManifestStaticFilesStorage` (hashed names, brotli, 1-year cache). `collectstatic` **fails if a CSS/JS file references a missing file** (e.g. a `sourceMappingURL` to an absent `.map`), and with `DEBUG=False` any `{% static %}` path not in the manifest raises. Check new static assets with `collectstatic` before deploying. Locally the setting only applies if `whitenoise` is installed.

### `chatbot/` — RAG chatbot
- `chatbot/views.py::chat_api_endpoint` (`POST /chatbot/api/chat/`, `{"message": ...}` → `{"response": ..., "sources": [...]}`; `sources` are `{section, url, item}` from `chatbot/rag/sources.py`, shown as chips and a "See …" link under the answer): per-IP rate limit (10/min via Django cache), 500-char limit, logs every turn to `ChatSession`/`ChatMessage` keyed by the Django session. Assistant turns store `ChatMessage.retrieval_meta` (routed question, intent, filters, chunk ids + scores, fallback, provider, per-stage latency).
- **Provider chain** (`chatbot/llm.py::make_llm`, used by `views.generate_llm_response` and the RAG pipeline): tries `CHATBOT_PROVIDER` env (else the enabled `Chatbot`'s `AIModelConfig.provider`), then every other provider that has an API key (openai → groq → gemini). If all fail, `chatbot/fallback.py::get_keyword_fallback_response` (hard-coded concept answers + DB keyword matching). Provider `mock` (DB or env) skips LLMs and RAG entirely.
- OpenAI and Groq share one cached `openai` SDK client (Groq via its OpenAI-compatible base URL); Gemini uses `google.generativeai`.
- **Env vars override DB config**: `<PROVIDER>_API_KEY` and `<PROVIDER>_MODEL` win over `AIModelConfig.api_key`/`model_name` (DB values have gone stale before — e.g. a retired Groq model). DB `temperature`/`api_base_url` apply only to the configured provider.
- Replies always pass through `chatbot/formatting.py::strip_markdown()` because `static/js/chat_widget.js` renders plain text (HTML-escaped, `
` → `<br>`). Keep replies plain-text and in V.E.R.A.'s assistant voice.

### `chatbot/rag/` — retrieval pipeline (`chatbot/rag_service.py` re-exports the entry points)
- **Source of truth is `knowledge_base/*.md`** (read-only, third person). One `## ` section = one chunk; each must start with a YAML block (`type`, `organization`, `period`, `tags`) or `ingest.py` raises `KnowledgeBaseError`. `period` formats parsed: `X to Y`, single year, `present`, `not specified`, `X and not specified`. `faq.md` chunks are identified by file (their `type` is e.g. `skill`); they embed only the question but pass question + answer to the LLM. The outdated `mynamesaravanaperumal@gmail.com` in the KB is rewritten to the current contact email at ingest. Also indexed: public GitHub repos (`chatbot/github_connector.py`, `RAG_INCLUDE_GITHUB`) and `ContextSnippet` rows (from `POST /update_context`) as `type: update`.
- **Index** (`index.py`): `faiss_index/` holds `index.faiss`, `chunks.json`, `manifest.json` (`chunk_id → content_hash` + embedding model). On first use the app compares the manifest to the KB files + snippets + model (not GitHub, to avoid a network call) and **rebuilds in-process with a warning if stale**, so a stale committed index is never served silently. Run `build_rag_index` after editing the KB to avoid that startup cost.
- **Models run on ONNX via fastembed, not PyTorch** — Render free has 512MB. Embeddings `BAAI/bge-small-en-v1.5` (queries get the bge "Represent this sentence…" prefix), reranker `Xenova/ms-marco-MiniLM-L-6-v2`. Both use `threads=1` and `enable_cpu_mem_arena=False`, and the reranker uses batch size 2: with the arena on, RSS grew past 1GB, and batch 20 spiked to ~640MB. Measured: ~375MB RSS with both models loaded. Models are cached in `.model_cache/` (gitignored, downloaded by `build_rag_index`).
- **Pipeline** (`pipeline.run`): one LLM call (`CONDENSE_ROUTE_PROMPT`, temperature 0, JSON) rewrites the message as a standalone third-person question and routes it (`lookup` / `list` / `timeframe` / `out_of_scope` / `chitchat`, `type_filter`, `year`); malformed JSON → plain lookup. `lookup`: dense top 20 + BM25 top 20 → RRF (k=60) → cross-encoder rerank → top 5 with at most 2 FAQ chunks. `list`: every non-FAQ chunk of the type, newest first, heading + first sentence. `timeframe`: filter by `start_year <= year <= end_year`, then lookup. If the top score (rerank logit, or dense cosine with the reranker off) is below `RAG_FALLBACK_THRESHOLD`, it returns `FALLBACK_MESSAGE` without generating. Prompts are in `prompts.py`: the system prompt, fixed lines and `FALLBACK_MESSAGE` follow the V.E.R.A. brand kit; keep its wording.
- The router often labels short in-scope questions ("where r u based", "how can i contact u") as `out_of_scope`/`chitchat`. With the reranker on, those intents still get a hybrid search, and a top rerank score ≥ `ROUTE_RESCUE_SCORE` (5.0) reroutes them to `lookup` (logged as `rerouted_from`). The eval numbers that set this and `DEFAULT_THRESHOLD_RERANK` (2.0) are in comments in `pipeline.py`. Re-check both if you change the models or the KB a lot.
- Eval: `chatbot/eval/golden_set.json` (50 visitor-style cases with `expected_chunk_ids`, optional `answer_must_include` regexes, `expect_refusal`) and `run_eval.py` (hit@5, MRR, DeepEval metrics, markdown/assistant-voice/refusal checks, threshold score distributions; reports go to `chatbot/eval/reports/`, gitignored).

## Configuration

`portfolio_hub/settings.py` loads `.env` with django-environ (`KEY=value`, no spaces around `=`; the file must end with a newline before appending lines). Keys used: `OPENAI_API_KEY`, `OPENAI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `GEMINI_API_KEY`, `CHATBOT_PROVIDER`, `UPDATE_TOKEN`, `GITHUB_USERNAME`, `GITHUB_TOKEN`, plus `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` (insecure dev defaults otherwise). `RENDER_EXTERNAL_HOSTNAME` is added to allowed hosts/CSRF origins on Render. `SQLITE_PATH` moves the database outside the checkout (EC2), `CSRF_TRUSTED_ORIGINS` (comma-separated) adds origins for a custom domain, and `SECURE_PROXY_SSL_HEADER` trusts the proxy's `X-Forwarded-Proto`. EC2 deployment: `aws.md`.

RAG settings: `RAG_INCLUDE_GITHUB` (default on), `RAG_RERANKER` (default on; `0` uses RRF order and dense-cosine fallback scoring), `RAG_FALLBACK_THRESHOLD` (overrides the default for whichever scorer is active: rerank logit or dense cosine — see `pipeline.DEFAULT_THRESHOLD_*`). `EVAL_JUDGE_MODEL` sets the DeepEval judge (default `gpt-4o-mini`).

On Render the filesystem resets on each deploy: `db.sqlite3` reverts to the committed copy, so `ContextSnippet` rows and live `/update_context` additions survive index rebuilds but not redeploys.
