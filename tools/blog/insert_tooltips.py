#!/usr/bin/env python3
"""Insert and validate the first glossary occurrence in each Markdown post.

The JSON dictionary is the only hand-edited tooltip source. Existing tooltip
spans are refreshed from it, and --check-coverage fails when a post is stale or
is missing an insertable first occurrence.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PARTICLES = (
    "으로부터", "에서부터", "에게서는", "으로는", "에서는", "까지는", "부터는",
    "이라면", "라면", "이라고", "라고", "이며", "이고", "처럼", "에게", "한테",
    "으로", "에서", "까지", "부터", "보다", "마다", "조차", "마저", "밖에",
    "은", "는", "이", "가", "을", "를", "의", "와", "과", "로", "도", "만",
)
PARTICLE_PATTERN = "|".join(map(re.escape, sorted(PARTICLES, key=len, reverse=True)))
TERM_SPAN_RE = re.compile(
    r'<span class="term" data-tip="([^"]*)">([^<]+)</span>'
)


def load_dict(path: str | os.PathLike[str]) -> dict[str, str]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not data:
        raise ValueError("tooltip dictionary must be a non-empty object")
    for term, tip in data.items():
        if not isinstance(term, str) or not term.strip():
            raise ValueError("tooltip term must be a non-empty string")
        if not isinstance(tip, str) or not tip.strip():
            raise ValueError(f"tooltip definition is empty: {term}")
        if any(char in tip for char in ('"', '<', '>')):
            raise ValueError(f"tooltip definition has an unsafe character: {term}")
    return data


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _fence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    active: tuple[str, int, int] | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^[ \t]{0,3}(`{3,}|~{3,})', line)
        if active is None and marker:
            token = marker.group(1)
            active = (token[0], len(token), offset)
        elif active is not None:
            char, length, start = active
            if re.match(rf'^[ \t]{{0,3}}{re.escape(char)}{{{length},}}[ \t]*\r?\n?$', line):
                spans.append((start, offset + len(line)))
                active = None
        offset += len(line)
    if active is not None:
        spans.append((active[2], len(text)))
    return spans


def _footnote_spans(text: str) -> list[tuple[int, int]]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)

    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if not re.match(r'^\[\^[^\]]+\]:', lines[index]):
            index += 1
            continue
        start = offsets[index]
        index += 1
        while index < len(lines):
            line = lines[index]
            if re.match(r'^(?: {2,}|\t)', line) or not line.strip():
                index += 1
                continue
            break
        end = offsets[index] if index < len(lines) else len(text)
        spans.append((start, end))
    return spans


def protected_spans(text: str) -> list[tuple[int, int]]:
    """Return merged Markdown ranges that must never be rewritten."""
    spans: list[tuple[int, int]] = []
    front_matter = re.match(r'^---\r?\n.*?\r?\n---\r?\n', text, re.S)
    if front_matter:
        spans.append(front_matter.span())
    spans.extend(_fence_spans(text))
    spans.extend(_footnote_spans(text))

    patterns = (
        r'`[^`\n]+`',
        r'<span class="term"[^>]*>.*?</span>',
        r'!?\[[^\]\n]*\]\([^\n)]*\)',
        r'^\[[^\]\n]+\]:\s*\S.*$',
        r'^#{1,6}\s+.*$',
        r'^>.*$',
        r'^_.*_$',
        r'<[^>]+>',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.M | re.S if "span" in pattern else re.M):
            spans.append(match.span())
    return _merge_spans(spans)


def _is_protected(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(span_start < end and span_end > start for span_start, span_end in spans)


def find_slot(text: str, term: str, spans: list[tuple[int, int]]):
    escaped = re.escape(term)
    previous = r'(?<![A-Za-z0-9_가-힣&-])'
    if re.search(r'[A-Za-z0-9]$', term):
        following = r'(?![A-Za-z0-9_-])'
    else:
        following = rf'(?:(?![A-Za-z0-9_가-힣-])|(?=(?:{PARTICLE_PATTERN})(?![가-힣])))'
    for match in re.finditer(previous + escaped + following, text):
        if not _is_protected(match.start(), match.end(), spans):
            return match
    return None


def _canonical_span(term: str, tip: str) -> str:
    return f'<span class="term" data-tip="{tip}">{term}</span>'


def transform(text: str, dictionary: dict[str, str]) -> tuple[str, int, int]:
    """Refresh existing spans, then add missing first occurrences."""
    updated = 0

    def refresh(match: re.Match[str]) -> str:
        nonlocal updated
        stored_tip = html.unescape(match.group(1))
        term = match.group(2)
        if term not in dictionary:
            return match.group(0)
        canonical = _canonical_span(term, dictionary[term])
        if stored_tip != dictionary[term] or match.group(0) != canonical:
            updated += 1
            return canonical
        return match.group(0)

    text = TERM_SPAN_RE.sub(refresh, text)
    added = 0
    for term in sorted(dictionary, key=lambda value: (-len(value), value.casefold())):
        if re.search(rf'<span class="term" data-tip="[^"]*">{re.escape(term)}</span>', text):
            continue
        match = find_slot(text, term, protected_spans(text))
        if not match:
            continue
        text = text[:match.start()] + _canonical_span(term, dictionary[term]) + text[match.end():]
        added += 1
    return text, added, updated


def validate_text(text: str, dictionary: dict[str, str] | None = None) -> tuple[int, list[str]]:
    errors: list[str] = []
    if re.search(r'data-tip="[^"]*data-tip', text):
        errors.append("nested data-tip")
    opened = text.count('<span class="term"')
    matched = list(TERM_SPAN_RE.finditer(text))
    if opened != len(matched):
        errors.append(f"unbalanced tooltip spans: {opened}!={len(matched)}")
    if re.search(r'\[[^\]]*<span class="term"[^\]]*\]\(', text):
        errors.append("tooltip span inside link label")
    if dictionary is not None:
        for match in matched:
            tip, term = html.unescape(match.group(1)), match.group(2)
            if term in dictionary and tip != dictionary[term]:
                errors.append(f"stale tooltip definition: {term}")
    return opened, errors


def _atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as fh:
        fh.write(text)
        temporary = fh.name
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("posts_dir")
    parser.add_argument("--dict", default=str(Path(__file__).with_name("tooltip_dict.json")))
    parser.add_argument("--check", action="store_true", help="validate existing markup only")
    parser.add_argument(
        "--check-coverage",
        action="store_true",
        help="fail if a post needs a missing tooltip insertion or dictionary refresh",
    )
    args = parser.parse_args()
    dictionary = load_dict(args.dict)
    total_added = total_updated = 0
    failed = False

    for path in sorted(Path(args.posts_dir).glob("*.md")):
        original = path.read_text(encoding="utf-8")
        transformed, added, updated = transform(original, dictionary)
        count, errors = validate_text(original if args.check else transformed, dictionary)
        if args.check_coverage and (added or updated):
            errors.append(f"tooltip coverage drift: +{added}, refresh={updated}")
        if not args.check and not args.check_coverage and transformed != original:
            _atomic_write(path, transformed)
        total_added += added
        total_updated += updated
        failed = failed or bool(errors)
        state = "OK" if not errors else "FAIL: " + "; ".join(errors)
        print(f"{path.name}: +{added}, refresh={updated}, total={count} {state}")

    print(f"tooltip check complete: added={total_added}, refreshed={total_updated}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
