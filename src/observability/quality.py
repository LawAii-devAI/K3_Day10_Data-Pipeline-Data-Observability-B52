from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run a suite of data quality checks on the dataframe and save report to data/quality/."""
    total_rows = len(df)

    # 1. Row count check
    row_count_passed = total_rows > 0

    # 2. paper_id check: not null and unique
    if "paper_id" in df.columns and total_rows > 0:
        paper_id_nulls = int(df["paper_id"].isna().sum() + (df["paper_id"] == "").sum())
        paper_id_duplicates = int(df["paper_id"].duplicated().sum())
    else:
        paper_id_nulls = total_rows
        paper_id_duplicates = 0

    paper_id_null_passed = (paper_id_nulls == 0) and (total_rows > 0)
    paper_id_unique_passed = (paper_id_duplicates == 0) and (total_rows > 0)

    # 3. title check: not null / not empty
    if "title" in df.columns and total_rows > 0:
        title_nulls = int(df["title"].isna().sum() + (df["title"] == "").sum())
    else:
        title_nulls = total_rows
    title_passed = (title_nulls == 0) and (total_rows > 0)

    # 4. summary check: length and not empty
    if "summary" in df.columns and total_rows > 0:
        summary_empty_count = int(df["summary"].isna().sum() + (df["summary"] == "").sum())
        avg_summary_len = float(df["summary"].astype(str).str.len().mean()) if total_rows > 0 else 0.0
    else:
        summary_empty_count = total_rows
        avg_summary_len = 0.0
    summary_passed = (summary_empty_count == 0) and (total_rows > 0)

    # 5. freshness check: age_days <= threshold
    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"].isna() | (df["age_days"] > threshold)).sum())
    else:
        stale_rows = total_rows
    freshness_passed = (stale_rows == 0) and (total_rows > 0)

    # Overall pass status
    all_passed = (
        row_count_passed
        and paper_id_null_passed
        and paper_id_unique_passed
        and title_passed
        and summary_passed
        and freshness_passed
    )

    payload = {
        "report_name": report_name,
        "timestamp": now_utc().isoformat(),
        "total_rows": total_rows,
        "passed": all_passed,
        "checks": {
            "row_count": {
                "passed": row_count_passed,
                "count": total_rows,
            },
            "paper_id_not_null": {
                "passed": paper_id_null_passed,
                "null_or_empty_count": paper_id_nulls,
            },
            "paper_id_unique": {
                "passed": paper_id_unique_passed,
                "duplicate_count": paper_id_duplicates,
            },
            "title_not_null": {
                "passed": title_passed,
                "null_or_empty_count": title_nulls,
            },
            "summary_valid": {
                "passed": summary_passed,
                "empty_count": summary_empty_count,
                "avg_character_length": round(avg_summary_len, 2),
            },
            "freshness": {
                "passed": freshness_passed,
                "stale_rows": stale_rows,
                "threshold_days": threshold,
            },
        },
    }

    file_name = report_name if report_name.endswith(".json") else f"{report_name}.json"
    output_path = settings.paths.quality_dir / file_name
    write_json(output_path, payload)

    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Aggregate freshness report and save JSON to report_path."""
    total_rows = len(df)
    threshold = settings.freshness_threshold_days

    latest_published = None
    oldest_published = None

    if not df.empty and "published" in df.columns:
        valid_dates = df["published"].dropna()
        valid_dates = valid_dates[valid_dates != ""]
        if not valid_dates.empty:
            latest_published = str(valid_dates.max())
            oldest_published = str(valid_dates.min())

    if not df.empty and "age_days" in df.columns:
        stale_rows = int((df["age_days"].isna() | (df["age_days"] > threshold)).sum())
    else:
        stale_rows = total_rows

    is_fresh = (stale_rows == 0) and (total_rows > 0)

    payload = {
        "timestamp": now_utc().isoformat(),
        "total_rows": total_rows,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    write_json(Path(report_path), payload)
    return payload

