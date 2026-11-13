"""Main pipeline entry point; orchestrates ingestion, chunking, embedding, storage and benchmark."""
import csv
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .store import PgVectorStore
from .evaluation import evaluate_query, summarize


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    repo_dir = root_dir.parent
    load_dotenv(root_dir / ".env")

    db_url = os.getenv("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is missing from starter/.env.")

    pdf_path = root_dir / "data" / "bother2025modyn.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"Corpus PDF not found at {pdf_path}")

    benchmark_path = root_dir / "data" / "benchmark.json"
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark questions not found at {benchmark_path}")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"==================================================")
    print(f" Day 06 · Data Ingestion Pipeline & Benchmark")
    print(f" Corpus: {pdf_path.name}")
    print(f" Benchmark questions: {len(questions)} (15 dev / 5 test)")
    print(f"==================================================")

    # 1. Ingestion
    print("\n[Step 1/5] Loading and normalizing PDF pages...")
    t0_ingest = time.time()
    pages = load_pdf(pdf_path, document_id="modyn_bother2025", source=pdf_path.name)
    ingest_time = round(time.time() - t0_ingest, 2)
    print(f" Loaded {len(pages)} pages in {ingest_time}s (Validates >= 30 pages: PASS)")

    # 2. Chunking
    print("\n[Step 2/5] Building chunking strategies...")
    # Strategy A: Fixed-size (500 chars, 50 overlap)
    chunks_a = []
    for p in pages:
        chunks_a.extend(fixed_size(p, size=500, overlap=50))
    print(f" Strategy A (Fixed size 500, overlap 50): {len(chunks_a)} chunks")

    # Strategy B: Structure-aware / By Paragraph (max 500 chars)
    chunks_b = []
    for p in pages:
        chunks_b.extend(by_paragraph(p, max_size=500))
    print(f" Strategy B (By paragraph max 500): {len(chunks_b)} chunks")

    # Strategy C uses Strategy B chunks with metadata filter
    print(f" Strategy C (By paragraph + Metadata filter): {len(chunks_b)} chunks")

    # 3. Embedder & Store
    print("\n[Step 3/5] Initializing Embedder and PostgreSQL + pgvector store...")
    embedder = MyEmbedder(model_name="models/gemini-embedding-001", api_key=gemini_key)
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
    store.create_schema()
    print(" Database schema and pgvector extension verified.")

    # Ingest Strategy A
    print("\n Embedding and storing Strategy A chunks...")
    t0_a = time.time()
    texts_a = [c.text for c in chunks_a]
    vecs_a = embedder.embed_documents(texts_a)
    store.upsert("strategy_a", chunks_a, vecs_a)
    time_a = round(time.time() - t0_a, 2)
    print(f" Strategy A indexed ({len(chunks_a)} chunks) in {time_a}s")

    # Ingest Strategy B & C (shared chunks, different retrieval filter)
    print("\n Embedding and storing Strategy B chunks...")
    t0_b = time.time()
    texts_b = [c.text for c in chunks_b]
    vecs_b = embedder.embed_documents(texts_b)
    store.upsert("strategy_b", chunks_b, vecs_b)
    time_b = round(time.time() - t0_b, 2)
    print(f" Strategy B indexed ({len(chunks_b)} chunks) in {time_b}s")

    # 4. Running Benchmark
    print("\n[Step 4/5] Running benchmark across 3 strategies...")
    # Pre-embed question queries
    print(" Embedding queries...")
    query_vectors = {}
    for q in questions:
        query_vectors[q["id"]] = embedder.embed_query(q["question"])

    results = {}
    strategies = [
        ("strategy_a", "Strategy A (Fixed-size, no filter)", False),
        ("strategy_b", "Strategy B (Paragraph-based, no filter)", False),
        ("strategy_c", "Strategy C (Paragraph-based + Metadata filter)", True),
    ]

    for strat_key, strat_name, use_filter in strategies:
        print(f"\n Evaluating {strat_name}...")
        traces = []
        target_store_strat = "strategy_b" if strat_key == "strategy_c" else strat_key

        for q in questions:
            q_vec = query_vectors[q["id"]]
            filters = q.get("filter") if use_filter else None
            hits = store.search(target_store_strat, q_vec, top_k=3, filters=filters)
            trace = evaluate_query(q, hits)
            traces.append(trace)

        summary = summarize(traces)
        results[strat_key] = {
            "name": strat_name,
            "traces": traces,
            "summary": summary
        }

        print(f"   Dev Hit@1:  {summary['dev']['hit_at_1_ratio']} ({summary['dev']['hit_at_1_pct']}%)")
        print(f"   Dev Hit@3:  {summary['dev']['hit_at_3_ratio']} ({summary['dev']['hit_at_3_pct']}%)")
        print(f"   Test Hit@1: {summary['test']['hit_at_1_ratio']} ({summary['test']['hit_at_1_pct']}%)")
        print(f"   Test Hit@3: {summary['test']['hit_at_3_ratio']} ({summary['test']['hit_at_3_pct']}%)")
        if summary.get("test", {}).get("filter_queries", 0) > 0:
            print(f"   Test Filter Compliance: {summary['test']['filter_compliant_ratio']} ({summary['test']['filter_compliant_pct']}%)")

    # 5. Saving Artifacts and Results
    print("\n[Step 5/5] Saving evaluation traces and reports...")
    results_dir = root_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = repo_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Save individual strategy traces
    for strat_key in ["strategy_a", "strategy_b", "strategy_c"]:
        trace_file = results_dir / f"traces_{strat_key}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(results[strat_key]["traces"], f, ensure_ascii=False, indent=2)

    # Save summary json
    summary_file = results_dir / "benchmark_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        export_summary = {k: v["summary"] for k, v in results.items()}
        json.dump(export_summary, f, ensure_ascii=False, indent=2)

    # Update experiment_log.csv
    exp_log_path = artifacts_dir / "experiment_log.csv"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(exp_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "strategy", "split", "hit_at_1", "hit_at_3", "chunk_count",
            "model", "dimensions", "cost_usd", "timestamp"
        ])
        for strat_key, strat_name, _ in strategies:
            s_data = results[strat_key]["summary"]
            c_count = len(chunks_a) if strat_key == "strategy_a" else len(chunks_b)
            for sp in ["dev", "test", "overall"]:
                sp_s = s_data[sp]
                writer.writerow([
                    strat_key,
                    sp,
                    sp_s["hit_at_1_ratio"],
                    sp_s["hit_at_3_ratio"],
                    c_count,
                    embedder.model_name,
                    embedder.dimensions,
                    0.0,
                    timestamp
                ])

    print("\n Pipeline and Benchmark completed successfully!")
    print(f" - Results saved to: {results_dir}")
    print(f" - Experiment log saved to: {exp_log_path}")


if __name__ == "__main__":
    main()
