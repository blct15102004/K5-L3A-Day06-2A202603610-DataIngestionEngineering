"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def is_evidence_match(gold_page: int, evidence_quote: str, hit: dict[str, Any]) -> bool:
    """Check if the hit matches gold page and contains sufficient evidence."""
    if hit.get("page") != gold_page:
        return False
    
    hit_text = hit.get("text", "").lower()
    quote = evidence_quote.lower().strip()
    
    if quote in hit_text:
        return True

    # Fallback for minor punctuation/whitespace differences
    words = [w for w in quote.split() if len(w) > 3]
    if len(words) >= 3:
        matched = sum(1 for w in words if w in hit_text)
        if matched / len(words) >= 0.8:
            return True
            
    return False


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace."""
    gold_page = question.get("gold_page")
    evidence_quote = question.get("evidence_quote", "")
    
    annotated_hits = []
    hit_1 = False
    hit_3 = False

    for rank, hit in enumerate(hits):
        hit_copy = dict(hit)
        is_hit = is_evidence_match(gold_page, evidence_quote, hit_copy)
        hit_copy["is_evidence_hit"] = is_hit
        annotated_hits.append(hit_copy)

        if rank == 0 and is_hit:
            hit_1 = True
        if rank < 3 and is_hit:
            hit_3 = True

    # Check filter compliance
    expected_filter = question.get("filter")
    filter_compliant = True
    if expected_filter:
        for hit in annotated_hits[:3]:
            hit_meta = hit.get("metadata", {})
            for k, v in expected_filter.items():
                if hit_meta.get(k) != v:
                    filter_compliant = False
                    break

    return {
        "question_id": question.get("id"),
        "split": question.get("split"),
        "question": question.get("question"),
        "expected_answer": question.get("expected_answer"),
        "gold_page": gold_page,
        "evidence_quote": evidence_quote,
        "filter": expected_filter,
        "hit_at_1": hit_1,
        "evidence_hit_at_3": hit_3,
        "filter_compliant": filter_compliant if expected_filter else None,
        "hits": annotated_hits
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    splits = ["dev", "test", "overall"]
    summary: dict[str, Any] = {}

    for sp in splits:
        if sp == "overall":
            sp_traces = traces
        else:
            sp_traces = [t for t in traces if t.get("split") == sp]

        n_total = len(sp_traces)
        if n_total == 0:
            continue

        n_hit_1 = sum(1 for t in sp_traces if t.get("hit_at_1"))
        n_hit_3 = sum(1 for t in sp_traces if t.get("evidence_hit_at_3"))

        # Filtered queries
        filtered_traces = [t for t in sp_traces if t.get("filter") is not None]
        n_filtered = len(filtered_traces)
        n_filter_ok = sum(1 for t in filtered_traces if t.get("filter_compliant"))

        summary[sp] = {
            "total_queries": n_total,
            "hit_at_1_count": n_hit_1,
            "hit_at_1_ratio": f"{n_hit_1}/{n_total}",
            "hit_at_1_pct": round(n_hit_1 / n_total * 100, 2),
            "hit_at_3_count": n_hit_3,
            "hit_at_3_ratio": f"{n_hit_3}/{n_total}",
            "hit_at_3_pct": round(n_hit_3 / n_total * 100, 2),
            "filter_queries": n_filtered,
            "filter_compliant_ratio": f"{n_filter_ok}/{n_filtered}" if n_filtered > 0 else "N/A",
            "filter_compliant_pct": round(n_filter_ok / n_filtered * 100, 2) if n_filtered > 0 else None
        }

    return summary
