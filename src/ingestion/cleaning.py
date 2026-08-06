from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return normalize_whitespace(str(value))


def _clean_list(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    result: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _normalize_date(value: Any) -> str:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return ""
    return parsed.date().isoformat()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Build a deterministic, embedding-ready DataFrame from raw records.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id", "title", "summary", "authors", "categories", "primary_category",
                "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
                "categories_joined", "summary_chars", "age_days", "text_for_embedding",
            ]
        )

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        if not paper_id or not title or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        summary = _clean_text(record.summary)
        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        published = _normalize_date(record.published)
        updated = _normalize_date(record.updated)
        published_timestamp = pd.to_datetime(published, errors="coerce", utc=True)
        age_days = None if pd.isna(published_timestamp) else max(0, (run_timestamp - published_timestamp).days)
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        embedding_parts = [f"Title: {title}"]
        if summary:
            embedding_parts.append(f"Summary: {summary}")
        if authors_joined:
            embedding_parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            embedding_parts.append(f"Categories: {categories_joined}")
        if published:
            embedding_parts.append(f"Published: {published}")

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0] if categories else _clean_text(record.primary_category),
                "published": published,
                "updated": updated,
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": "\n".join(embedding_parts),
            }
        )

    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category",
        "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
        "categories_joined", "summary_chars", "age_days", "text_for_embedding",
    ]
    dataframe = pd.DataFrame(rows, columns=columns)
    if dataframe.empty:
        return dataframe
    return dataframe.sort_values(["published", "paper_id"], ascending=[False, True], na_position="last").reset_index(drop=True)
