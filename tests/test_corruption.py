from __future__ import annotations

import json

import pandas as pd
import pytest

from ingestion.corruption import (
    CorruptionConfig,
    corrupt_clean_dataframe,
    repair_clean_dataframe,
    validate_repaired_dataframe,
)


@pytest.fixture
def clean_df() -> pd.DataFrame:
    rows = []
    for index in range(10):
        title = f"A sufficiently long paper title {index}"
        summary = f"Useful abstract about retrieval and agents {index}."
        rows.append(
            {
                "paper_id": f"doi-{index}",
                "title": title,
                "summary": summary,
                "published": f"2026-01-{index + 1:02d}",
                "age_days": 100 - index,
                "authors_joined": "Ada, Linus",
                "categories_joined": "AI, RAG",
                "summary_chars": len(summary),
                "text_for_embedding": f"{title}\n{summary}\nAda, Linus\nAI, RAG",
            }
        )
    return pd.DataFrame(rows)


def test_corruption_is_reproducible_and_writes_audit_log(clean_df, tmp_path):
    first_log = tmp_path / "first.json"
    second_log = tmp_path / "second.json"

    first = corrupt_clean_dataframe(clean_df, first_log)
    second = corrupt_clean_dataframe(clean_df, second_log)

    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(clean_df, clean_df.copy())

    log = json.loads(first_log.read_text())
    assert log["input_rows"] == 10
    assert {scenario["type"] for scenario in log["scenarios"]} == {
        "drop_latest_records",
        "blank_summary",
        "inject_summary_noise",
        "truncate_title",
        "stale_published_date",
        "duplicate_rows",
    }
    assert first["paper_id"].duplicated().any()
    assert first["summary"].eq("").any()
    assert first["summary"].str.contains("CORRUPTED_NOISE", regex=False).any()
    assert first["text_for_embedding"].str.contains("CORRUPTED_NOISE", regex=False).any()


def test_repair_restores_trusted_snapshot_and_writes_validation(clean_df, tmp_path):
    corrupted = corrupt_clean_dataframe(clean_df, tmp_path / "corruption.json")
    repair_log = tmp_path / "repair.json"

    repaired = repair_clean_dataframe(corrupted, clean_df, repair_log)

    pd.testing.assert_frame_equal(repaired, clean_df.reset_index(drop=True))
    assert validate_repaired_dataframe(repaired, clean_df)["is_valid"] is True
    assert json.loads(repair_log.read_text())["validation"]["same_content"] is True


def test_rejects_invalid_schema(clean_df, tmp_path):
    with pytest.raises(ValueError, match="missing required columns"):
        corrupt_clean_dataframe(clean_df.drop(columns="paper_id"), tmp_path / "log.json")


def test_zero_fractions_leave_content_unchanged(clean_df, tmp_path):
    config = CorruptionConfig(
        latest_fraction=0,
        blank_summary_fraction=0,
        noisy_summary_fraction=0,
        truncated_title_fraction=0,
        stale_date_fraction=0,
        duplicate_fraction=0,
    )
    result = corrupt_clean_dataframe(clean_df, tmp_path / "log.json", config)
    expected = clean_df.copy()
    # Corruption owns the canonical rebuild of this derived field.
    expected["text_for_embedding"] = expected.apply(
        lambda row: "\n".join(
            [row["title"], row["summary"], row["authors_joined"], row["categories_joined"]]
        ),
        axis=1,
    )
    pd.testing.assert_frame_equal(result, expected)
