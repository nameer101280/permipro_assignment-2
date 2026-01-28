"""Routing and search logic for the question-answering API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional
import json
import re

from .data import load_geo_rows, load_regulation_text


GEO_KEYWORDS = {
    "geo",
    "geodata",
    "map",
    "kaart",
    "bodem",
    "grond",
    "mobiscore",
    "overstrom",
    "water",
    "weg",
    "lucht",
    "hoogte",
    "distance",
    "overlap",
}

REGULATION_KEYWORDS = {
    "regulation",
    "verordening",
    "artikel",
    "art.",
    "bouw",
    "bouwvlak",
    "bouwlaag",
    "bosdecreet",
    "groen",
    "vergunning",
    "voorschrift",
    "bestemming",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "is",
    "are",
    "wat",
    "waar",
    "hoe",
    "een",
    "de",
    "het",
    "en",
    "met",
    "van",
    "op",
    "ik",
    "we",
}

PREFERRED_API_KEYS = [
    "naam",
    "name",
    "id",
    "gid",
    "height",
    "score",
    "projectnummer",
    "fasedatum",
    "svnaam",
    "legende",
    "wegcategorie",
    "wegsegmentstatus",
]


@dataclass
class AnswerResult:
    answer: str
    source: str


def route_question(question: str) -> str:
    """Return the best matching source for the question."""
    text = question.lower()
    geo_score = sum(1 for kw in GEO_KEYWORDS if kw in text)
    reg_score = sum(1 for kw in REGULATION_KEYWORDS if kw in text)

    if geo_score == 0 and reg_score == 0:
        return "unknown"
    if geo_score == reg_score:
        return "unknown"
    return "geo" if geo_score > reg_score else "regulation"


def answer_question(question: str) -> AnswerResult:
    source = route_question(question)
    if source == "geo":
        answer = search_geo(question)
    elif source == "regulation":
        answer = search_regulation(question)
    else:
        answer = "I could not determine which data source applies to that question."
    return AnswerResult(answer=answer, source=source)


def search_geo(question: str) -> str:
    rows = load_geo_rows()
    tokens = extract_keywords(question)
    best_row = None
    best_score = 0

    for row in rows:
        haystack = " ".join(
            [
                row.get("name", ""),
                row.get("status", ""),
                row.get("distance_m", ""),
                row.get("overlap_fraction", ""),
                row.get("api_name", ""),
            ]
        ).lower()
        score = score_tokens(tokens, haystack)
        if score > best_score:
            best_score = score
            best_row = row

    if not best_row or best_score == 0:
        return "No relevant geo match found in the mock data."

    return format_geo_answer(best_row)


def search_regulation(question: str) -> str:
    text = load_regulation_text()
    blocks = split_blocks(text)
    tokens = extract_keywords(question)

    article_match = match_article_reference(question)
    if article_match:
        for block in blocks:
            if block.lower().startswith(article_match):
                return format_regulation_answer(block)

    best_block = None
    best_score = 0
    for block in blocks:
        score = score_tokens(tokens, block.lower())
        if score > best_score:
            best_score = score
            best_block = block

    if not best_block or best_score == 0:
        return "No relevant regulation match found in the mock data."

    return format_regulation_answer(best_block)


def extract_keywords(question: str) -> list:
    words = re.findall(r"[a-zA-Z0-9]+", question.lower())
    return [word for word in words if word not in STOPWORDS and len(word) > 2]


def score_tokens(tokens: Iterable[str], text: str) -> int:
    return sum(1 for token in tokens if token in text)


def split_blocks(text: str) -> list:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def match_article_reference(question: str) -> Optional[str]:
    match = re.search(r"art\.?\s*(\d+(?:\.\d+)?)", question.lower())
    if not match:
        return None
    number = match.group(1)
    return f"art. {number}".lower()


def format_geo_answer(row: dict) -> str:
    name = safe_value(row.get("name")) or "(unknown name)"
    status = safe_value(row.get("status"))
    distance = safe_value(row.get("distance_m"))
    overlap = safe_value(row.get("overlap_fraction"))

    details = []
    if status:
        details.append(f"status={status}")
    if distance:
        details.append(f"distance_m={distance}")
    if overlap:
        details.append(f"overlap_fraction={overlap}")

    api_summary = summarize_api_name(row.get("api_name"))
    if api_summary:
        details.append(f"details={api_summary}")

    detail_text = "; ".join(details)
    if detail_text:
        return f"Match in geo data: {name}. {detail_text}."
    return f"Match in geo data: {name}."


def safe_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.upper() == "NULL":
        return None
    return cleaned


def summarize_api_name(raw_value: Optional[str]) -> Optional[str]:
    cleaned = safe_value(raw_value)
    if not cleaned:
        return None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    items = []
    for key in PREFERRED_API_KEYS:
        if key in data and data[key] not in (None, ""):
            items.append((key, data[key]))
        if len(items) >= 3:
            break

    if not items:
        for key in sorted(data.keys()):
            value = data[key]
            if value in (None, ""):
                continue
            if isinstance(value, (str, int, float)):
                items.append((key, value))
            if len(items) >= 3:
                break

    if not items:
        return None

    return ", ".join(f"{key}={value}" for key, value in items)


def format_regulation_answer(block: str) -> str:
    snippet = collapse_whitespace(block)
    if len(snippet) > 300:
        snippet = snippet[:297].rsplit(" ", 1)[0] + "..."
    return f"From regulation data: {snippet}"


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())
