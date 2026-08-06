from __future__ import annotations

from core.config import load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()
    require_llm_credentials(settings)

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=settings.paths.embeddings_json)

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary={
            "source_api": settings.source_api,
            "query": settings.source_query,
            "raw_count": len(records),
            "clean_count": len(df),
        },
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_questions = [item["question"] for item in read_json(settings.paths.eval_testset)[:3]]
    try:
        agent = build_agent(settings, index)
        demo_answers = [{"question": q, "answer": run_agent_question(agent, q)} for q in demo_questions]
        write_json(settings.paths.demo_answers, demo_answers)
    except Exception as exc:
        print(f"Skipping agent demo (optional step): {exc}")

    print(f"Phase 1 complete: {len(df)} papers indexed.")
    print(f"Baseline metrics: {bundle.summary}")
