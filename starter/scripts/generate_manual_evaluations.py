"""
Script: generate_manual_evaluations.py
Tạo các file đánh giá thủ công từ traces đã có cho corpus bài báo Modyn (bother2025modyn.pdf):
1. coherence_evaluation.json  — đánh giá độ mạch lạc chunk (0-2) cho 10 vị trí
2. grounding_evaluation.json  — đánh giá grounding cho 5 câu test (0-2)
3. metadata_check.json        — kiểm tra metadata đầy đủ và đúng (top-3 hits cho 5 câu test)
"""

import json
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")

def load_traces(strategy):
    path = os.path.join(RESULTS_DIR, f"traces_strategy_{strategy}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

traces_a = load_traces("a")
traces_b = load_traces("b")
traces_c = load_traces("c")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Coherence Evaluation (10 vị trí trang cố định)
# Trang: 1, 3, 5, 8, 10, 12, 14, 17, 20, 24
# Rubric:
#  2 = Tự đủ nghĩa, câu cú hoàn chỉnh, context rõ ràng
#  1 = Đủ dùng nhưng bị cắt câu hoặc thiếu context phụ
#  0 = Bị cắt giữa ý chính, không hiểu được nếu thiếu chunk trước/sau
# ─────────────────────────────────────────────────────────────────────────────

COHERENCE_ASSESSMENTS = {
    1: {
        "a": {
            "chunk_id": "modyn_bother2025_p1_fix_000",
            "text_preview": "Modyn: Data-Centric Machine Learning Pipeline Orchestration MAXIMILIAN BÖTHER, ETH Zurich...",
            "score": 2,
            "reason": "Title, authors and abstract opening. Self-contained introduction to Modyn."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p1_par_000",
            "text_preview": "Modyn: Data-Centric Machine Learning Pipeline Orchestration MAXIMILIAN BÖTHER, ETH Zurich...",
            "score": 2,
            "reason": "Complete title and metadata block, completely self-contained."
        }
    },
    3: {
        "a": {
            "chunk_id": "modyn_bother2025_p3_fix_000",
            "text_preview": "transparently by a platform, while ML users focus on defining the logic of ML training... We present Modyn...",
            "score": 1,
            "reason": "Fixed-window cuts into the middle of a sentence at the top of page 3."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p3_par_000",
            "text_preview": "We present Modyn, a data-centric machine learning pipeline orchestrator that addresses this gap...",
            "score": 2,
            "reason": "Paragraph boundary begins neatly at the introduction of Modyn's contributions."
        }
    },
    5: {
        "a": {
            "chunk_id": "modyn_bother2025_p5_fix_000",
            "text_preview": "is given as St = (s1,...,snt). Each sample si in St comprises a unique identifier, a label, a timestamp...",
            "score": 1,
            "reason": "Cuts mid-equation from previous page, but definition of sample si is readable."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p5_par_001",
            "text_preview": "Triggering. The triggering policy decides whether to trigger a new training. We model a triggering policy as a function pi...",
            "score": 2,
            "reason": "Complete paragraph introducing Triggering policy definition formally."
        }
    },
    8: {
        "a": {
            "chunk_id": "modyn_bother2025_p8_fix_000",
            "text_preview": "Fig. 3. Modyn's system design. stores data samples streaming in from external sources in its storage...",
            "score": 1,
            "reason": "Contains figure caption and part of architecture description, cuts mid-sentence."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p8_par_001",
            "text_preview": "Example pipeline. Figure 4 shows a declaratively-specified Modyn pipeline. At minimum, a description comprises...",
            "score": 2,
            "reason": "Self-contained paragraph explaining the 7 declarative components of a pipeline."
        }
    },
    10: {
        "a": {
            "chunk_id": "modyn_bother2025_p10_fix_000",
            "text_preview": "covariate shift, i.e., they compare the distribution of the incoming data to some reference data. We leverage the evidently...",
            "score": 1,
            "reason": "Starts mid-sentence from page 9 continuation, explains drift libraries."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p10_par_001",
            "text_preview": "Data drift variants. For unstructured data such as images, we transform it into a latent embedding space...",
            "score": 2,
            "reason": "Well-defined paragraph covering how drift detection applies to unstructured image data."
        }
    },
    12: {
        "a": {
            "chunk_id": "modyn_bother2025_p12_fix_000",
            "text_preview": "Backends for presampling. For implementing presampling strategies, Modyn provides two backends that share an interface...",
            "score": 2,
            "reason": "Starts at section header and cleanly introduces Postgres and local backends."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p12_par_000",
            "text_preview": "Backends for presampling. For implementing presampling strategies, Modyn provides two backends...",
            "score": 2,
            "reason": "Clean paragraph explaining presampling backends in full."
        }
    },
    14: {
        "a": {
            "chunk_id": "modyn_bother2025_p14_fix_000",
            "text_preview": "In order to avoid data stalls when the data loader requests data, each worker (or dataset instance) implements a prefetching...",
            "score": 1,
            "reason": "Explains prefetching but cuts off before discussing partition buffer mechanics."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p14_par_000",
            "text_preview": "In order to avoid data stalls when the data loader requests data, each worker (or dataset instance) implements a prefetching mechanism...",
            "score": 2,
            "reason": "Full paragraph discussing prefetching mechanism, partition buffers, and gRPC streaming."
        }
    },
    17: {
        "a": {
            "chunk_id": "modyn_bother2025_p17_fix_000",
            "text_preview": "Evaluation Year Model trained on data up to Accuracy % Fig. 7. Accuracy matrix for yearbook full data training...",
            "score": 1,
            "reason": "Mixes OCR figure labels with beginning of text discussion on underfitting."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p17_par_001",
            "text_preview": "50 % subset training. Figure 8 shows composite model accuracies per selection strategy in a boxplot. Generally, the uncertainty based downsamplers...",
            "score": 2,
            "reason": "Complete discussion comparing uncertainty downsamplers on 50% subset."
        }
    },
    20: {
        "a": {
            "chunk_id": "modyn_bother2025_p20_fix_000",
            "text_preview": "Number of triggers Mean Accuracy % Time Drift Amount Performance Fig. 12. Feasible set of triggering policies...",
            "score": 1,
            "reason": "Contains raw plot text fragments before starting the discussion on performance triggers."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p20_par_001",
            "text_preview": "Performance-based triggers. These triggers fire when the model performance on a window drops below a threshold...",
            "score": 2,
            "reason": "Clear, complete paragraph explaining performance-based triggering mechanics."
        }
    },
    24: {
        "a": {
            "chunk_id": "modyn_bother2025_p24_fix_000",
            "text_preview": "Throughput Modyn Optimal (a) Criteo (x1000) Data Workers Throughput (b) CGLM Fig. 16. Modyn throughput vs. optimal...",
            "score": 1,
            "reason": "Fragmented chart labels followed by partial conclusion."
        },
        "b": {
            "chunk_id": "modyn_bother2025_p24_par_002",
            "text_preview": "8 CONCLUSION AND FUTURE WORK. We present the data-centric Modyn orchestrator for ML pipelines on growing datasets...",
            "score": 2,
            "reason": "Self-contained conclusion summary and future work outlook."
        }
    }
}

pages = sorted(COHERENCE_ASSESSMENTS.keys())
avg_a = sum(COHERENCE_ASSESSMENTS[p]["a"]["score"] for p in pages) / len(pages)
avg_b = sum(COHERENCE_ASSESSMENTS[p]["b"]["score"] for p in pages) / len(pages)

coherence_output = {
    "description": "Manual coherence evaluation (0=cut mid-thought, 1=acceptable but minor context missing, 2=self-contained)",
    "sampled_pages": pages,
    "strategy_a_avg": round(avg_a, 2),
    "strategy_b_avg": round(avg_b, 2),
    "detail": {str(p): COHERENCE_ASSESSMENTS[p] for p in pages}
}

with open(os.path.join(ARTIFACTS_DIR, "coherence_evaluation.json"), "w", encoding="utf-8") as f:
    json.dump(coherence_output, f, ensure_ascii=False, indent=2)
print(f"[OK] coherence_evaluation.json -> avg_a={avg_a:.2f}, avg_b={avg_b:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Metadata Check (Top-3 hits of 5 test queries)
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ["source", "page", "section", "topic", "component"]

def check_metadata(hit):
    meta = hit.get("metadata", {})
    return (bool(hit.get("source")) and
            hit.get("page") is not None and
            bool(meta.get("section")) and
            bool(meta.get("topic")) and
            bool(meta.get("component")))

metadata_results = {}
for strat_name, traces in [("a", traces_a), ("b", traces_b), ("c", traces_c)]:
    test_traces = [t for t in traces if t["split"] == "test"]
    total_hits = 0
    complete_hits = 0
    filter_total = 0
    filter_ok = 0
    per_q = []

    for item in test_traces:
        hits = item.get("hits", [])[:3]
        q_filter = item.get("filter")
        q_res = {
            "question_id": item["question_id"],
            "filter": q_filter,
            "hits_checked": len(hits),
            "complete_count": 0,
            "filter_compliant": None
        }
        for h in hits:
            total_hits += 1
            if check_metadata(h):
                complete_hits += 1
                q_res["complete_count"] += 1

        if q_filter:
            filter_total += 1
            compliant = all(h.get("metadata", {}).get(k) == v for k, v in q_filter.items() for h in hits) if hits else False
            q_res["filter_compliant"] = compliant
            if compliant:
                filter_ok += 1
        per_q.append(q_res)

    metadata_results[f"strategy_{strat_name}"] = {
        "total_hits": total_hits,
        "complete_hits": complete_hits,
        "complete_pct": round(complete_hits / total_hits * 100, 1) if total_hits else 0,
        "filter_questions": filter_total,
        "filter_compliant": filter_ok,
        "per_question": per_q
    }

with open(os.path.join(ARTIFACTS_DIR, "metadata_check.json"), "w", encoding="utf-8") as f:
    json.dump(metadata_results, f, ensure_ascii=False, indent=2)

for sn in ["a", "b", "c"]:
    r = metadata_results[f"strategy_{sn}"]
    print(f"[OK] strategy_{sn}: meta={r['complete_hits']}/{r['total_hits']}, filter={r['filter_compliant']}/{r['filter_questions']}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Grounding Quality (5 test questions x 3 strategies)
# ─────────────────────────────────────────────────────────────────────────────

GROUNDING_MANUAL = {
    "q16": {
        "question": "What triggering policy function does Modyn formally model, and what does it output?",
        "strategy_a": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 contains the exact mathematical definition on page 5."},
        "strategy_b": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 has the full triggering policy formula paragraph."},
        "strategy_c": {"scores": [2, 2, 1], "avg": 1.67, "note": "Filter section=system_design narrows results to formalization pages."}
    },
    "q17": {
        "question": "What is the BinaryFileWrapper in Modyn optimized for?",
        "strategy_a": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 contains the endianness and ifstream optimization text on page 15."},
        "strategy_b": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 contains the exact paragraph discussing BinaryFileWrapper."},
        "strategy_c": {"scores": [2, 2, 0], "avg": 1.33, "note": "Filter keeps top hits within system_design section."}
    },
    "q18": {
        "question": "What was the best selection strategy result on CGLM-landmark for the 25% subset?",
        "strategy_a": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 on page 19 contains the 25% subset DLIS (33.7%) and RS2 (33.6%) numbers."},
        "strategy_b": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 paragraph has the exact takeaway statistics."},
        "strategy_c": {"scores": [2, 1, 0], "avg": 1.0, "note": "No filter on q18; behaves identical to B."}
    },
    "q19": {
        "question": "What models does Modyn ship with out of the box?",
        "strategy_a": {"scores": [1, 1, 0], "avg": 0.67, "note": "Hits mention ResNets and DLRM, but split across chunks."},
        "strategy_b": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 has Trainer Server paragraph mentioning ResNets, DLRM, transformers."},
        "strategy_c": {"scores": [2, 2, 1], "avg": 1.67, "note": "Section filter isolates the Trainer Server component description."}
    },
    "q20": {
        "question": "What throughput does Modyn achieve for the Criteo recommendation system dataset relative to optimal?",
        "strategy_a": {"scores": [2, 0, 0], "avg": 0.67, "note": "Hit 1 has the over 70% optimal throughput sentence on page 24."},
        "strategy_b": {"scores": [2, 1, 0], "avg": 1.0, "note": "Hit 1 contains the complete conclusion of Criteo throughput benchmark."},
        "strategy_c": {"scores": [2, 1, 0], "avg": 1.0, "note": "No filter on q20; behaves identical to B."}
    }
}

grounding_summary = {}
for sn in ["strategy_a", "strategy_b", "strategy_c"]:
    all_sc = []
    for qid, d in GROUNDING_MANUAL.items():
        all_sc.extend(d[sn]["scores"])
    grounding_summary[sn] = {
        "avg_score": round(sum(all_sc) / len(all_sc), 2),
        "count_0": all_sc.count(0),
        "count_1": all_sc.count(1),
        "count_2": all_sc.count(2),
        "total_hits": len(all_sc)
    }

grounding_output = {
    "summary": grounding_summary,
    "per_question": GROUNDING_MANUAL
}

with open(os.path.join(ARTIFACTS_DIR, "grounding_evaluation.json"), "w", encoding="utf-8") as f:
    json.dump(grounding_output, f, ensure_ascii=False, indent=2)

for sn in ["strategy_a", "strategy_b", "strategy_c"]:
    s = grounding_summary[sn]
    print(f"[OK] {sn}: avg_grounding={s['avg_score']}, 0={s['count_0']}, 1={s['count_1']}, 2={s['count_2']}")

print("\n=== Manual evaluations successfully generated ===")
