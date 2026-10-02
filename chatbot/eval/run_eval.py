"""
Evaluate the chatbot's RAG pipeline against chatbot/eval/golden_set.json.

Calls the pipeline functions directly (no HTTP, so no rate limit) with the real index, models and
LLM provider chain. Reports retrieval hit rate@5 / MRR, DeepEval ContextualRecall, ContextualPrecision,
Faithfulness and AnswerRelevancy, markdown / first-person / refusal checks, and the score
distributions used to pick RAG_FALLBACK_THRESHOLD. Writes a JSON report to chatbot/eval/reports/.

    pip install -r requirements-dev.txt
    python chatbot/eval/run_eval.py                  # full run (DeepEval judge = gpt-4o-mini via OPENAI_API_KEY)
    python chatbot/eval/run_eval.py --no-deepeval    # retrieval + rule checks only, no judge calls
    python chatbot/eval/run_eval.py --limit 5 --no-reranker
"""
import argparse
import asyncio
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portfolio_hub.settings")
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

import django  # noqa: E402

django.setup()

from chatbot.models import Chatbot  # noqa: E402
from chatbot.rag import index as rag_index  # noqa: E402
from chatbot.rag import pipeline  # noqa: E402
from chatbot.rag.prompts import CONTACT_EMAIL, FALLBACK_MESSAGE  # noqa: E402
from chatbot.rag.retrieve import hybrid_search  # noqa: E402
from chatbot.llm import make_llm  # noqa: E402

GOLDEN_SET = Path(__file__).with_name("golden_set.json")
REPORT_DIR = Path(__file__).with_name("reports")

TARGETS = {"hit_rate_at_5": 0.9, "faithfulness": 0.9}

# Markdown the widget can't render (numbered "1." lines are allowed: the prompt asks for one item per line)
MARKDOWN_RE = re.compile(r"(\*\*|__|`|^\s{0,3}#{1,6}\s|^\s*[-*•]\s|^\s*\|.*\|\s*$)", re.M)
FIRST_PERSON_RE = re.compile(r"\b(I|I'm|I've|I'd|I'll|my|me|mine)\b")
THIRD_PERSON_RE = re.compile(r"\b(he|his|him)\b|\bSaravana (is|was|has|had|did|worked|built|studied)\b", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s-]{8,}\d)")
REFUSAL_PHRASES = ("only cover", "professional background", "don't have", "do not have", "not able to share",
                   "can't share", "cannot share", "not something i", "won't share", "i don't share", CONTACT_EMAIL)


def load_cases(limit=None):
    cases = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    return cases[:limit] if limit else cases


def retrieval_metrics(case, retrieved_ids, intent):
    expected = case["expected_chunk_ids"]
    if not expected:
        return None
    # List answers pass every matching chunk to the LLM, so the whole list counts as "the top k"
    ranked = retrieved_ids if intent == "list" else retrieved_ids[:5]
    rank = next((i for i, cid in enumerate(ranked, 1) if cid in expected), None)
    return {"hit_at_5": rank is not None, "reciprocal_rank": 1 / rank if rank else 0.0, "first_hit_rank": rank}


def rule_checks(case, result):
    reply, raw = result["reply"] or "", result["raw_reply"] or ""
    meta = result["meta"]
    checks = {"markdown_free": not MARKDOWN_RE.search(raw) if raw and raw != FALLBACK_MESSAGE else True}
    answered = reply and reply != FALLBACK_MESSAGE
    if case.get("expect_refusal"):
        lowered = reply.lower()
        checks["refused"] = bool(
            not PHONE_RE.search(reply) and (
                meta["fallback"] or meta["intent"] == "out_of_scope" or any(p in lowered for p in REFUSAL_PHRASES)
            )
        )
    else:
        checks["answered"] = bool(answered)
        if answered:
            checks["first_person"] = bool(FIRST_PERSON_RE.search(reply)) and not THIRD_PERSON_RE.search(reply)
    for pattern in case.get("answer_must_include", []):
        checks[f"includes:{pattern}"] = bool(re.search(pattern, reply, re.I))
    for pattern in case.get("answer_must_not_include", []):
        checks[f"excludes:{pattern}"] = not re.search(pattern, reply, re.I)
    if case.get("expected_intent"):
        checks[f"intent={case['expected_intent']}"] = meta["intent"] == case["expected_intent"]
    return checks


async def deepeval_scores(rows, store, judge_model, concurrency=6):
    from deepeval.metrics import (
        AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric, FaithfulnessMetric,
    )
    from deepeval.test_case import LLMTestCase

    by_id = {c["chunk_id"]: c for c in store.chunks}
    semaphore = asyncio.Semaphore(concurrency)
    metric_classes = {
        "contextual_recall": ContextualRecallMetric,
        "contextual_precision": ContextualPrecisionMetric,
        "faithfulness": FaithfulnessMetric,
        "answer_relevancy": AnswerRelevancyMetric,
    }

    async def score(row, name, cls):
        case = row["case"]
        expected_output = by_id[case["expected_chunk_ids"][0]]["display_text"]
        test_case = LLMTestCase(
            input=case["question"], actual_output=row["reply"], expected_output=expected_output,
            retrieval_context=row["context_texts"] or ["(no sources)"],
        )
        metric = cls(model=judge_model, include_reason=True, async_mode=True)
        async with semaphore:
            try:
                await metric.a_measure(test_case, _show_indicator=False)
                row["deepeval"][name] = {"score": metric.score, "reason": metric.reason}
            except Exception as e:  # one judge failure shouldn't kill the run
                row["deepeval"][name] = {"score": None, "reason": f"judge error: {e}"}

    jobs = []
    for row in rows:
        row["deepeval"] = {}
        if row["case"].get("expect_refusal") or not row["case"]["expected_chunk_ids"]:
            continue
        if not row["reply"] or row["reply"] == FALLBACK_MESSAGE:
            continue  # fallback replies are judged by the rule checks, not DeepEval
        jobs += [score(row, name, cls) for name, cls in metric_classes.items()]
    await asyncio.gather(*jobs)


def threshold_analysis(rows):
    in_scope = sorted(r["forced_top_score"] for r in rows
                      if r["forced_top_score"] is not None and r["case"]["category"] != "out_of_scope")
    out_scope = sorted(r["forced_top_score"] for r in rows
                       if r["forced_top_score"] is not None and r["case"]["category"] == "out_of_scope")
    if not in_scope or not out_scope:
        return {"in_scope": in_scope, "out_of_scope": out_scope, "suggested": None}
    gap_low, gap_high = max(out_scope), min(in_scope)
    suggested = round((gap_low + gap_high) / 2, 2) if gap_high > gap_low else None
    return {
        "in_scope": [round(s, 3) for s in in_scope],
        "out_of_scope": [round(s, 3) for s in out_scope],
        "in_scope_min": round(gap_high, 3),
        "out_of_scope_max": round(gap_low, 3),
        "separable": gap_high > gap_low,
        "suggested": suggested,
    }


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="Only run the first N cases")
    parser.add_argument("--no-deepeval", action="store_true", help="Skip the LLM-judged DeepEval metrics")
    parser.add_argument("--judge-model", default=os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"))
    parser.add_argument("--no-reranker", action="store_true", help="Evaluate with RAG_RERANKER off")
    args = parser.parse_args()

    use_reranker = not args.no_reranker and rag_index.reranker_enabled()
    store = rag_index.get_store()
    bot = Chatbot.objects.select_related("model_config").filter(enabled=True).first()
    llm = make_llm(bot.model_config if bot else None)
    cases = load_cases(args.limit)

    rows = []
    started = time.time()
    for i, case in enumerate(cases, 1):
        result = pipeline.run(case["question"], [], llm, store=store, use_reranker=use_reranker)
        meta = result["meta"]
        retrieved = [c["chunk_id"] for c in meta["chunks"]]
        # Score every question as a lookup too, to compare in-scope vs out-of-scope score distributions
        _, forced_top = hybrid_search(store, meta["standalone_question"], use_reranker=use_reranker)
        row = {
            "case": case,
            "reply": result["reply"],
            "raw_reply": result["raw_reply"],
            "route": {k: meta[k] for k in ("standalone_question", "intent", "type_filter", "year")},
            "retrieved": [(c["chunk_id"], c["score"]) for c in meta["chunks"]],
            "context_texts": [r["text"] for r in result["results"]],
            "top_score": meta["top_score"],
            "forced_top_score": forced_top,
            "fallback": meta["fallback"],
            "provider": meta["provider"],
            "latency_ms": meta["latency_ms"],
            "retrieval": retrieval_metrics(case, retrieved, meta["intent"]),
            "checks": rule_checks(case, result),
        }
        rows.append(row)
        status = "ok" if all(row["checks"].values()) and (row["retrieval"] or {}).get("hit_at_5", True) else "FAIL"
        print(f"[{i:>2}/{len(cases)}] {status:<4} {meta['intent']:<12} {case['question'][:60]}", flush=True)

    if not args.no_deepeval:
        print(f"\nRunning DeepEval metrics with judge {args.judge_model}...", flush=True)
        asyncio.run(deepeval_scores(rows, store, args.judge_model))

    retrieval_rows = [r for r in rows if r["retrieval"]]
    oos_rows = [r for r in rows if r["case"].get("expect_refusal")]
    answered = [r for r in rows if r["reply"] and r["reply"] != FALLBACK_MESSAGE and not r["case"].get("expect_refusal")]
    summary = {
        "cases": len(rows),
        "reranker": use_reranker,
        "judge_model": None if args.no_deepeval else args.judge_model,
        "hit_rate_at_5": mean([float(r["retrieval"]["hit_at_5"]) for r in retrieval_rows]),
        "mrr": mean([r["retrieval"]["reciprocal_rank"] for r in retrieval_rows]),
        "fallback_on_in_scope": sum(r["fallback"] for r in rows if not r["case"].get("expect_refusal")),
        "out_of_scope_refused": f"{sum(r['checks']['refused'] for r in oos_rows)}/{len(oos_rows)}",
        "markdown_free": f"{sum(r['checks']['markdown_free'] for r in rows)}/{len(rows)}",
        "first_person": f"{sum(r['checks'].get('first_person', False) for r in answered)}/{len(answered)}",
        "median_latency_ms": sorted(r["latency_ms"].get("total_ms", 0) for r in rows)[len(rows) // 2],
        "runtime_s": round(time.time() - started, 1),
    }
    if not args.no_deepeval:
        for name in ("contextual_recall", "contextual_precision", "faithfulness", "answer_relevancy"):
            summary[name] = mean([r["deepeval"].get(name, {}).get("score") for r in rows])
    summary["threshold"] = threshold_analysis(rows)
    summary["targets_met"] = {
        "hit_rate_at_5>=0.9": (summary["hit_rate_at_5"] or 0) >= TARGETS["hit_rate_at_5"],
        "faithfulness>=0.9": None if args.no_deepeval else (summary.get("faithfulness") or 0) >= TARGETS["faithfulness"],
        "all_out_of_scope_refused": all(r["checks"]["refused"] for r in oos_rows),
    }

    failures = []
    for r in rows:
        problems = [k for k, ok in r["checks"].items() if not ok]
        if r["retrieval"] and not r["retrieval"]["hit_at_5"]:
            problems.append("retrieval_miss")
        for name, d in r.get("deepeval", {}).items():
            if d.get("score") is not None and d["score"] < 0.5:
                problems.append(f"{name}={d['score']:.2f}")
        if problems:
            failures.append({"question": r["case"]["question"], "category": r["case"]["category"],
                             "intent": r["route"]["intent"], "problems": problems,
                             "retrieved": [cid for cid, _ in r["retrieved"][:5]], "reply": r["reply"]})

    REPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = REPORT_DIR / f"eval-{stamp}.json"
    report_path.write_text(json.dumps({"summary": summary, "failures": failures, "rows": rows},
                                      indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    print("\n=== Summary ===")
    for key, value in summary.items():
        if key != "threshold":
            print(f"{key:<22} {value}")
    t = summary["threshold"]
    print(f"threshold              in-scope min {t.get('in_scope_min')}, out-of-scope max {t.get('out_of_scope_max')}, "
          f"suggested {t.get('suggested')}")
    print(f"\n=== Failures ({len(failures)}) ===")
    for f in failures:
        print(f"- [{f['category']}/{f['intent']}] {f['question']}: {', '.join(f['problems'])}")
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
