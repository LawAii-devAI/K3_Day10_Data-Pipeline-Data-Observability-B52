from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


@dataclass(frozen=True)
class CorruptionConfig:
    """Parameters for a deterministic, reproducible corruption run."""

    seed: int = 42
    latest_fraction: float = 0.15
    blank_summary_fraction: float = 0.20
    noisy_summary_fraction: float = 0.20
    truncated_title_fraction: float = 0.20
    stale_date_fraction: float = 0.20
    duplicate_fraction: float = 0.15
    stale_days: int = 730
    title_max_chars: int = 18
    noise_marker: str = " [CORRUPTED_NOISE] xqzv 000 ???"

    def __post_init__(self) -> None:
        fractions = (
            self.latest_fraction,
            self.blank_summary_fraction,
            self.noisy_summary_fraction,
            self.truncated_title_fraction,
            self.stale_date_fraction,
            self.duplicate_fraction,
        )
        if any(value < 0 or value > 1 for value in fractions):
            raise ValueError("Corruption fractions must be between 0 and 1.")
        if self.stale_days <= 0 or self.title_max_chars <= 0:
            raise ValueError("stale_days and title_max_chars must be positive.")


REQUIRED_COLUMNS = {"paper_id", "title", "summary", "published", "text_for_embedding"}


def _validate_dataframe(df: pd.DataFrame, *, name: str) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _sample_count(row_count: int, fraction: float, *, max_count: int | None = None) -> int:
    if row_count == 0 or fraction == 0:
        return 0
    count = max(1, round(row_count * fraction))
    return min(count, row_count if max_count is None else max_count)


def _record_ids(df: pd.DataFrame, indexes: list[Any]) -> list[str]:
    return [str(value) for value in df.loc[indexes, "paper_id"].tolist()]


def _rebuild_text_for_embedding(df: pd.DataFrame) -> None:
    """Rebuild embedding input after corrupting fields used by retrieval."""

    def build_text(row: pd.Series) -> str:
        fields = (
            ("Title", "title"),
            ("Summary", "summary"),
            ("Authors", "authors_joined"),
            ("Categories", "categories_joined"),
            ("Published", "published"),
        )
        parts: list[str] = []
        for label, column in fields:
            if column not in df:
                continue
            value = row.get(column, "")
            if pd.isna(value) or not str(value).strip():
                continue
            parts.append(f"{label}: {str(value).strip()}")
        return "\n".join(parts)

    df["text_for_embedding"] = df.apply(build_text, axis=1)


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: str | Path,
    config: CorruptionConfig | None = None,
) -> pd.DataFrame:
    """Create reproducibly corrupted data without modifying the input dataframe.

    The scenarios deliberately affect completeness, validity, freshness, uniqueness,
    and the text used by retrieval. A machine-readable audit log is always written.
    """

    _validate_dataframe(df, name="df")
    settings = config or CorruptionConfig()
    corrupted = df.copy(deep=True).reset_index(drop=True)
    scenarios: list[dict[str, Any]] = []

    # Remove the newest records, but retain at least one row when input is non-empty.
    parsed_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = _sample_count(
        len(corrupted), settings.latest_fraction, max_count=max(0, len(corrupted) - 1)
    )
    latest_indexes = parsed_dates.sort_values(ascending=False, na_position="last").index[:drop_count].tolist()
    scenarios.append(
        {
            "type": "drop_latest_records",
            "count": len(latest_indexes),
            "record_ids": _record_ids(corrupted, latest_indexes),
            "parameters": {"fraction": settings.latest_fraction},
        }
    )
    corrupted = corrupted.drop(index=latest_indexes).reset_index(drop=True)

    generator = pd.Series(range(len(corrupted)))

    def sample_indexes(fraction: float, salt: int) -> list[int]:
        count = _sample_count(len(corrupted), fraction)
        if count == 0:
            return []
        return generator.sample(n=count, random_state=settings.seed + salt).tolist()

    blank_indexes = sample_indexes(settings.blank_summary_fraction, 1)
    corrupted.loc[blank_indexes, "summary"] = ""
    if "summary_chars" in corrupted:
        corrupted.loc[blank_indexes, "summary_chars"] = 0
    scenarios.append(
        {
            "type": "blank_summary",
            "count": len(blank_indexes),
            "record_ids": _record_ids(corrupted, blank_indexes),
            "parameters": {"fraction": settings.blank_summary_fraction},
        }
    )

    noise_indexes = sample_indexes(settings.noisy_summary_fraction, 2)
    corrupted.loc[noise_indexes, "summary"] = (
        corrupted.loc[noise_indexes, "summary"].fillna("").astype(str) + settings.noise_marker
    )
    if "summary_chars" in corrupted:
        corrupted.loc[noise_indexes, "summary_chars"] = corrupted.loc[
            noise_indexes, "summary"
        ].str.len()
    scenarios.append(
        {
            "type": "inject_summary_noise",
            "count": len(noise_indexes),
            "record_ids": _record_ids(corrupted, noise_indexes),
            "parameters": {
                "fraction": settings.noisy_summary_fraction,
                "noise_marker": settings.noise_marker,
            },
        }
    )

    title_indexes = sample_indexes(settings.truncated_title_fraction, 3)
    corrupted.loc[title_indexes, "title"] = corrupted.loc[title_indexes, "title"].map(
        lambda value: str(value)[: settings.title_max_chars]
    )
    scenarios.append(
        {
            "type": "truncate_title",
            "count": len(title_indexes),
            "record_ids": _record_ids(corrupted, title_indexes),
            "parameters": {
                "fraction": settings.truncated_title_fraction,
                "max_chars": settings.title_max_chars,
            },
        }
    )

    stale_indexes = sample_indexes(settings.stale_date_fraction, 4)
    original_dates = pd.to_datetime(corrupted.loc[stale_indexes, "published"], errors="coerce")
    stale_dates = original_dates - pd.to_timedelta(settings.stale_days, unit="D")
    valid_stale = stale_dates.notna()
    applied_stale_indexes = stale_dates.index[valid_stale].tolist()
    corrupted.loc[applied_stale_indexes, "published"] = stale_dates.loc[valid_stale].map(
        lambda value: value.isoformat()
    )
    if "age_days" in corrupted:
        numeric_age = pd.to_numeric(corrupted.loc[applied_stale_indexes, "age_days"], errors="coerce")
        corrupted.loc[applied_stale_indexes, "age_days"] = numeric_age + settings.stale_days
    scenarios.append(
        {
            "type": "stale_published_date",
            "count": len(applied_stale_indexes),
            "record_ids": _record_ids(corrupted, applied_stale_indexes),
            "parameters": {
                "fraction": settings.stale_date_fraction,
                "days_subtracted": settings.stale_days,
            },
        }
    )

    _rebuild_text_for_embedding(corrupted)

    duplicate_indexes = sample_indexes(settings.duplicate_fraction, 5)
    duplicates = corrupted.loc[duplicate_indexes].copy(deep=True)
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    scenarios.append(
        {
            "type": "duplicate_rows",
            "count": len(duplicate_indexes),
            "record_ids": _record_ids(duplicates.reset_index(drop=True), list(range(len(duplicates)))),
            "parameters": {"fraction": settings.duplicate_fraction},
        }
    )

    write_json(
        Path(output_log_path),
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "seed": settings.seed,
            "input_rows": len(df),
            "output_rows": len(corrupted),
            "config": asdict(settings),
            "scenarios": scenarios,
        },
    )
    return corrupted


def validate_repaired_dataframe(repaired_df: pd.DataFrame, trusted_df: pd.DataFrame) -> dict[str, Any]:
    """Return explicit evidence that repaired data matches the trusted clean source."""

    _validate_dataframe(repaired_df, name="repaired_df")
    _validate_dataframe(trusted_df, name="trusted_df")
    same_columns = list(repaired_df.columns) == list(trusted_df.columns)
    same_rows = len(repaired_df) == len(trusted_df)
    same_ids = repaired_df["paper_id"].tolist() == trusted_df["paper_id"].tolist()
    same_content = repaired_df.equals(trusted_df)
    return {
        "is_valid": same_columns and same_rows and same_ids and same_content,
        "same_columns": same_columns,
        "same_row_count": same_rows,
        "same_ordered_paper_ids": same_ids,
        "same_content": same_content,
        "repaired_rows": len(repaired_df),
        "trusted_rows": len(trusted_df),
    }


def repair_clean_dataframe(
    corrupted_df: pd.DataFrame,
    trusted_df: pd.DataFrame,
    output_log_path: str | Path | None = None,
) -> pd.DataFrame:
    """Restore clean data from a trusted baseline snapshot and validate the result.

    Reconstructing from a trusted source avoids guessing which corrupted values are
    correct. ``corrupted_df`` is validated and retained only as audit context.
    """

    _validate_dataframe(corrupted_df, name="corrupted_df")
    _validate_dataframe(trusted_df, name="trusted_df")
    if trusted_df["paper_id"].duplicated().any():
        raise ValueError("trusted_df contains duplicate paper_id values.")

    repaired = trusted_df.copy(deep=True).reset_index(drop=True)
    trusted = trusted_df.copy(deep=True).reset_index(drop=True)
    validation = validate_repaired_dataframe(repaired, trusted)
    if not validation["is_valid"]:
        raise RuntimeError("Repair validation failed.")

    if output_log_path is not None:
        write_json(
            Path(output_log_path),
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "strategy": "restore_from_trusted_clean_snapshot",
                "corrupted_rows": len(corrupted_df),
                "validation": validation,
            },
        )
    return repaired
