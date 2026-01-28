"""Routing and search logic for the question-answering API."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional
import json
import re
import time

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
    "rivier",
    "gebied",
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
    "sloop",
    "omgevingsvergunning",
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
    "what",
    "which",
    "define",
    "explain",
    "over",
    "about",
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

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
ARTICLE_RE = re.compile(r"art\.?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass
class GeoEntry:
    name: str
    status: Optional[str]
    distance_m: Optional[str]
    overlap_fraction: Optional[str]
    api_name_raw: Optional[str]
    api_name_dict: Optional[dict]
    tokens: set[str]


@dataclass
class RegulationBlock:
    raw: str
    title: str
    article_id: Optional[str]
    tokens: set[str]


@dataclass
class SearchResult:
    answer: str
    top_matches: list[dict]
    best_score: int
    matched_id: Optional[str] = None


@dataclass
class AnswerResult:
    answer: str
    source: str
    meta: dict


def answer_question(question: str, top_k: int = 3) -> AnswerResult:
    start = time.perf_counter()
    tokens = set(extract_keywords(question))
    geo_entries = get_geo_entries()
    reg_blocks = get_regulation_blocks()

    geo_total, reg_total, article_ref = compute_route_scores(
        question, tokens, geo_entries, reg_blocks
    )
    source = decide_source(geo_total, reg_total)

    if source == "geo":
        search_result = search_geo(question, top_k=top_k)
        data_file = "mock_geo_data.csv"
    elif source == "regulation":
        search_result = search_regulation(
            question, top_k=top_k, article_ref=article_ref
        )
        data_file = "mock_regulation_data.txt"
    else:
        search_result = SearchResult(
            answer="I could not determine which data source applies to that question.",
            top_matches=[],
            best_score=0,
        )
        data_file = None

    route_confidence = compute_route_confidence(geo_total, reg_total)
    match_confidence = compute_match_confidence(
        search_result.best_score, len(tokens), search_result.matched_id is not None
    )
    if source == "unknown":
        confidence = 0.0
    else:
        confidence = round((route_confidence + match_confidence) / 2, 2)

    processing_ms = int((time.perf_counter() - start) * 1000)

    meta = {
        "confidence": confidence,
        "route_confidence": route_confidence,
        "match_confidence": match_confidence,
        "route_scores": {"geo": geo_total, "regulation": reg_total},
        "top_matches": search_result.top_matches,
        "processing_ms": processing_ms,
        "data_file": data_file,
    }

    if search_result.matched_id:
        meta["matched_article"] = search_result.matched_id

    return AnswerResult(answer=search_result.answer, source=source, meta=meta)


def route_question(question: str) -> str:
    geo_total, reg_total, _ = compute_route_scores(
        question, set(extract_keywords(question)), get_geo_entries(), get_regulation_blocks()
    )
    return decide_source(geo_total, reg_total)


def search_geo(question: str, top_k: int = 3) -> SearchResult:
    entries = get_geo_entries()
    tokens = set(extract_keywords(question))
    question_norm = normalize_phrase(question)

    matches = []
    for entry in entries:
        score = score_match(tokens, entry.tokens, phrase_boost(entry.name, question_norm))
        if score:
            matches.append((score, entry))

    matches.sort(key=lambda item: item[0], reverse=True)
    top_k = clamp_top_k(top_k)

    if not matches:
        return SearchResult(
            answer="No relevant geo match found in the mock data.",
            top_matches=[],
            best_score=0,
        )

    best_score, best_entry = matches[0]
    top_matches = [format_geo_match(entry, score) for score, entry in matches[:top_k]]
    answer = format_geo_answer(best_entry)

    return SearchResult(answer=answer, top_matches=top_matches, best_score=best_score)


def search_regulation(
    question: str, top_k: int = 3, article_ref: Optional[str] = None
) -> SearchResult:
    blocks = get_regulation_blocks()
    tokens = set(extract_keywords(question))
    question_norm = normalize_phrase(question)
    article_ref = article_ref or match_article_reference(question)

    matches = []
    for block in blocks:
        score = score_match(tokens, block.tokens, phrase_boost(block.title, question_norm))
        if article_ref and block.article_id == article_ref:
            score += 10
        if score:
            matches.append((score, block))

    matches.sort(key=lambda item: item[0], reverse=True)
    top_k = clamp_top_k(top_k)

    if not matches:
        return SearchResult(
            answer="No relevant regulation match found in the mock data.",
            top_matches=[],
            best_score=0,
        )

    best_score, best_block = matches[0]
    top_matches = [
        format_regulation_match(block, score) for score, block in matches[:top_k]
    ]
    answer = format_regulation_answer(best_block)
    matched_id = article_ref if article_ref and best_block.article_id == article_ref else None

    return SearchResult(
        answer=answer,
        top_matches=top_matches,
        best_score=best_score,
        matched_id=matched_id,
    )


def compute_route_scores(
    question: str,
    tokens: set[str],
    geo_entries: list[GeoEntry],
    reg_blocks: list[RegulationBlock],
) -> tuple[int, int, Optional[str]]:
    geo_kw = keyword_score(question, GEO_KEYWORDS)
    reg_kw = keyword_score(question, REGULATION_KEYWORDS)
    geo_match = best_overlap_score(tokens, [entry.tokens for entry in geo_entries])
    reg_match = best_overlap_score(tokens, [block.tokens for block in reg_blocks])
    article_ref = match_article_reference(question)

    geo_total = geo_kw * 2 + geo_match
    reg_total = reg_kw * 2 + reg_match + (4 if article_ref else 0)

    return geo_total, reg_total, article_ref


def decide_source(geo_total: int, reg_total: int) -> str:
    if geo_total == 0 and reg_total == 0:
        return "unknown"
    if abs(geo_total - reg_total) <= 1:
        return "unknown"
    return "geo" if geo_total > reg_total else "regulation"


def compute_route_confidence(geo_total: int, reg_total: int) -> float:
    max_total = max(geo_total, reg_total)
    if max_total == 0:
        return 0.0
    confidence = (max_total - min(geo_total, reg_total)) / max_total
    return round(confidence, 2)


def compute_match_confidence(
    best_score: int, token_count: int, article_match: bool
) -> float:
    if article_match:
        return 1.0
    if token_count <= 0:
        return 0.0
    return min(1.0, round(best_score / token_count, 2))


def keyword_score(question: str, keywords: Iterable[str]) -> int:
    text = question.lower()
    return sum(1 for keyword in keywords if keyword in text)


def best_overlap_score(tokens: set[str], token_sets: Iterable[set[str]]) -> int:
    if not tokens:
        return 0
    best = 0
    for token_set in token_sets:
        overlap = len(tokens & token_set)
        if overlap > best:
            best = overlap
    return best


def score_match(tokens: set[str], entry_tokens: set[str], boost: int) -> int:
    return len(tokens & entry_tokens) + boost


def phrase_boost(phrase: str, question_norm: str) -> int:
    if not phrase:
        return 0
    normalized = normalize_phrase(phrase)
    if len(normalized) < 4:
        return 0
    return 3 if normalized and normalized in question_norm else 0


def extract_keywords(question: str) -> list[str]:
    tokens = TOKEN_RE.findall(question.lower())
    filtered = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token.isdigit() and len(token) == 1:
            continue
        if len(token) <= 2:
            continue
        filtered.append(token)
    return filtered


def normalize_phrase(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def split_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def match_article_reference(question: str) -> Optional[str]:
    match = ARTICLE_RE.search(question)
    if not match:
        return None
    number = match.group(1)
    return f"art. {number}".lower()


def clamp_top_k(top_k: int) -> int:
    if top_k <= 0:
        return 3
    return min(top_k, 5)


@lru_cache(maxsize=1)
def get_geo_entries() -> list[GeoEntry]:
    entries: list[GeoEntry] = []
    for row in load_geo_rows():
        name = safe_value(row.get("name")) or ""
        status = safe_value(row.get("status"))
        distance = safe_value(row.get("distance_m"))
        overlap = safe_value(row.get("overlap_fraction"))
        api_raw = safe_value(row.get("api_name"))
        api_dict = parse_api_name(api_raw)

        combined = " ".join(
            value
            for value in [name, status, distance, overlap, api_raw]
            if value
        )
        tokens = set(extract_keywords(combined))

        entries.append(
            GeoEntry(
                name=name,
                status=status,
                distance_m=distance,
                overlap_fraction=overlap,
                api_name_raw=api_raw,
                api_name_dict=api_dict,
                tokens=tokens,
            )
        )
    return entries


@lru_cache(maxsize=1)
def get_regulation_blocks() -> list[RegulationBlock]:
    text = load_regulation_text()
    blocks = []
    for raw_block in split_blocks(text):
        lines = raw_block.splitlines()
        title = lines[0].strip() if lines else raw_block[:60]
        article_id = extract_article_id(raw_block)
        tokens = set(extract_keywords(raw_block))
        blocks.append(
            RegulationBlock(
                raw=raw_block,
                title=title,
                article_id=article_id,
                tokens=tokens,
            )
        )
    return blocks


def extract_article_id(text: str) -> Optional[str]:
    match = ARTICLE_RE.search(text)
    if not match:
        return None
    return f"art. {match.group(1)}".lower()


def format_geo_answer(entry: GeoEntry) -> str:
    name = entry.name or "(unknown name)"
    details = []
    if entry.status:
        details.append(f"status={entry.status}")
    if entry.distance_m:
        details.append(f"distance_m={entry.distance_m}")
    if entry.overlap_fraction:
        details.append(f"overlap_fraction={entry.overlap_fraction}")

    api_summary = summarize_api_name(entry.api_name_dict)
    if api_summary:
        details.append(f"details={api_summary}")

    detail_text = "; ".join(details)
    if detail_text:
        return f"Match in geo data: {name}. {detail_text}."
    return f"Match in geo data: {name}."


def format_geo_match(entry: GeoEntry, score: int) -> dict:
    return {
        "name": entry.name or "(unknown name)",
        "score": score,
        "status": entry.status,
        "distance_m": entry.distance_m,
        "overlap_fraction": entry.overlap_fraction,
        "details": summarize_api_name(entry.api_name_dict),
    }


def format_regulation_answer(block: RegulationBlock) -> str:
    snippet = collapse_whitespace(block.raw)
    if len(snippet) > 300:
        snippet = snippet[:297].rsplit(" ", 1)[0] + "..."
    return f"From regulation data: {snippet}"


def format_regulation_match(block: RegulationBlock, score: int) -> dict:
    snippet = collapse_whitespace(block.raw)
    if len(snippet) > 160:
        snippet = snippet[:157].rsplit(" ", 1)[0] + "..."
    return {
        "title": block.title,
        "article": block.article_id,
        "score": score,
        "snippet": snippet,
    }


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def safe_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.upper() == "NULL":
        return None
    return cleaned


def parse_api_name(raw_value: Optional[str]) -> Optional[dict]:
    if not raw_value:
        return None
    try:
        data = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def summarize_api_name(api_name_dict: Optional[dict]) -> Optional[str]:
    if not api_name_dict:
        return None

    items = []
    for key in PREFERRED_API_KEYS:
        value = api_name_dict.get(key)
        if value not in (None, ""):
            items.append((key, value))
        if len(items) >= 3:
            break

    if not items:
        for key in sorted(api_name_dict.keys()):
            value = api_name_dict[key]
            if value in (None, ""):
                continue
            if isinstance(value, (str, int, float)):
                items.append((key, value))
            if len(items) >= 3:
                break

    if not items:
        return None

    return ", ".join(f"{key}={value}" for key, value in items)
