from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _list_text(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a deterministic evaluation set from the cleaned corpus.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if len(df) < 2:
        raise ValueError("At least 2 cleaned documents are required to build an evaluation set.")

    required_columns = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = sorted(required_columns.difference(df.columns))
    if missing:
        raise ValueError(f"Cleaned dataframe is missing required columns: {', '.join(missing)}")

    # Keep the set compact and deterministic so all three pipeline states use identical questions.
    selected = df.sort_values("paper_id", kind="stable").head(8)
    test_set: list[dict[str, Any]] = []

    for row in selected.to_dict(orient="records"):
        paper_id = _text(row.get("paper_id"))
        title = _text(row.get("title"))
        if not paper_id or not title:
            continue
        title_ref = f"'{title}'"

        summary = _text(row.get("summary"))
        if summary:
            test_set.append(
                {
                    "id": f"{paper_id}::summary",
                    "question_type": "summary",
                    "question": f"What is the summary of the paper {title_ref}?",
                    "ground_truth": first_sentence(summary),
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        authors = _text(row.get("authors_joined"))
        if authors:
            test_set.append(
                {
                    "id": f"{paper_id}::authors",
                    "question_type": "authors",
                    "question": f"Who authored the paper {title_ref}?",
                    "ground_truth": authors,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        published = _text(row.get("published"))
        if published:
            test_set.append(
                {
                    "id": f"{paper_id}::date",
                    "question_type": "date",
                    "question": f"When was the paper {title_ref} published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        categories = _text(row.get("categories_joined"))
        if categories:
            test_set.append(
                {
                    "id": f"{paper_id}::categories",
                    "question_type": "categories",
                    "question": f"What categories does the paper {title_ref} have?",
                    "ground_truth": categories,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not test_set:
        raise ValueError("No valid evaluation samples could be built from the cleaned dataframe.")
    write_json(output_path, test_set)
    return test_set
