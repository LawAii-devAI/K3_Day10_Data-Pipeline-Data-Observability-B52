from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import re
from pathlib import Path
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _as_text(value: Any) -> str:
    """Convert Crossref's optional scalar/list text fields to clean text."""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item is not None)
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _as_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _date_from_crossref(value: Any) -> str:
    """Return an ISO date from Crossref's ``date-parts`` structure."""
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return ""
    raw_parts = parts[0]
    try:
        year = int(raw_parts[0])
        month = int(raw_parts[1]) if len(raw_parts) > 1 else 1
        day = int(raw_parts[2]) if len(raw_parts) > 2 else 1
        return datetime(year, month, day).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return ""


def _paper_date(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _date_from_crossref(item.get(key))
        if value:
            return value
    return ""


def _paper_from_item(item: dict[str, Any]) -> PaperRecord | None:
    paper_id = _as_text(item.get("DOI")).lower()
    title_values = item.get("title")
    title = _as_text(title_values[0] if isinstance(title_values, list) and title_values else title_values)
    if not paper_id or not title:
        return None

    authors: list[str] = []
    for author in item.get("author", []):
        if not isinstance(author, dict):
            continue
        name = _as_text(author.get("name"))
        if not name:
            given = _as_text(author.get("given"))
            family = _as_text(author.get("family"))
            name = _as_text(" ".join(part for part in (given, family) if part))
        if name and name not in authors:
            authors.append(name)

    categories = _as_list(item.get("subject"))
    links = item.get("link", [])
    abs_url = _as_text(item.get("URL")) or f"https://doi.org/{paper_id}"
    pdf_url = ""
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            url = _as_text(link.get("URL"))
            content_type = _as_text(link.get("content-type")).lower()
            if url and (content_type == "application/pdf" or url.lower().split("?", 1)[0].endswith(".pdf")):
                pdf_url = url
                break

    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=_as_text(item.get("abstract")),
        authors=authors,
        categories=categories,
        primary_category=categories[0] if categories else "",
        published=_paper_date(item, "published", "published-print", "published-online", "issued"),
        updated=_paper_date(item, "updated"),
        abs_url=abs_url,
        pdf_url=pdf_url,
        comment=_as_text(item.get("comment")),
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works response into stable ``PaperRecord`` objects.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        raise ValueError("Crossref payload message.items must be a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _paper_from_item(item)
        if record is None or record.paper_id in seen_ids:
            continue
        seen_ids.add(record.paper_id)
        records.append(record)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works, persist raw artifacts, and return parsed records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "day10-data-observability-lab/0.1",
    }
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504}:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                if attempt < 3:
                    time.sleep(min(delay, 30.0))
                    continue
            elif response.status_code >= 400:
                response.raise_for_status()
            response.raise_for_status()
            payload = response.json()
            records = parse_crossref_payload(payload)
            write_json(settings.paths.raw_api_response, payload)
            write_json(settings.paths.raw_records_json, [record.__dict__ for record in records])
            return records
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            break
    raise RuntimeError(f"Failed to fetch or parse Crossref data after 4 attempts: {last_error}") from last_error


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the parsed raw-record snapshot written by ``fetch_source_records``."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("Raw records snapshot must contain a JSON list.")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            PaperRecord(
                paper_id=_as_text(item.get("paper_id")).lower(),
                title=_as_text(item.get("title")),
                summary=_as_text(item.get("summary")),
                authors=_as_list(item.get("authors")),
                categories=_as_list(item.get("categories")),
                primary_category=_as_text(item.get("primary_category")),
                published=_as_text(item.get("published")),
                updated=_as_text(item.get("updated")),
                abs_url=_as_text(item.get("abs_url")),
                pdf_url=_as_text(item.get("pdf_url")),
                comment=_as_text(item.get("comment")),
            )
        )
    return records
