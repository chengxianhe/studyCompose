from __future__ import annotations

from govplatform.evaluation.models import CaseResult


def ranking_metrics(ranked: list[str], relevant: list[str]) -> tuple[float, float]:
    if not relevant:
        raise ValueError("ranking metrics require positive labels")
    unique = list(dict.fromkeys(ranked))
    recall = len(set(unique[:5]) & set(relevant)) / len(set(relevant))
    reciprocal = next((1 / rank for rank, key in enumerate(unique[:10], 1) if key in relevant), 0.0)
    return recall, reciprocal


def aggregate(results: list[CaseResult]) -> dict[str, float | int | None]:
    positive = [result for result in results if result.expected]
    scored = [result for result in positive if result.recall_at_5 is not None]
    negative = [result for result in results if not result.expected]
    graded = [result for result in negative if result.no_answer_correct is not None]
    return {
        "total_cases": len(results),
        "positive_cases": len(positive),
        "scored_positive_cases": len(scored),
        "mean_recall_at_5": sum(r.recall_at_5 or 0 for r in scored) / len(scored)
        if scored
        else None,
        "mean_mrr_at_10": sum(r.mrr_at_10 or 0 for r in scored) / len(scored) if scored else None,
        "unanswerable_cases": len(negative),
        "graded_unanswerable_cases": len(graded),
        "unanswerable_false_passes": sum(r.no_answer_correct is False for r in graded)
        if graded
        else None,
        "unanswerable_correct": sum(r.no_answer_correct is True for r in graded)
        if graded
        else None,
        "failed_or_degraded_cases": sum(r.status != "ok" for r in results),
        "lifecycle_violations": sum(len(r.lifecycle_violations) for r in results),
        "mean_query_ms": sum(r.elapsed_ms for r in results) / len(results) if results else None,
    }
