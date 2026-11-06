"""Retrieval metrics only; synthetic scores are not challenge performance."""
import numpy as np


def precision_recall_at_k(retrieved, relevant, k):
    if k < 1:
        raise ValueError("Positive k required")
    relevant = set(relevant)
    if not relevant:
        return {"precision": None, "recall": None}
    found = set(retrieved[:k]) & relevant
    return {"precision": len(found) / k, "recall": len(found) / len(relevant)}


def summarize(cases, k):
    eligible = [c for c in cases if c[f"precision@{k}"] is not None and not c.get("error")]
    durations = [c["latency_ms"] for c in cases if not c.get("error")]
    return {
        "questions_total": len(cases), "questions_scored": len(eligible),
        "errors": sum(bool(c.get("error")) for c in cases),
        f"precision@{k}": float(np.mean([c[f"precision@{k}"] for c in eligible])) if eligible else None,
        f"recall@{k}": float(np.mean([c[f"recall@{k}"] for c in eligible])) if eligible else None,
        "latency_ms_p50": float(np.percentile(durations, 50)) if durations else None,
        "latency_ms_p95": float(np.percentile(durations, 95)) if durations else None,
        "latency_n": len(durations), "percentile_method": "numpy linear",
    }
