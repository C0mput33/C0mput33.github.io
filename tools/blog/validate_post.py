#!/usr/bin/env python3
"""Validate Jekyll posts before publication."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import yaml


REQUIRED_FIELDS = ("title", "date", "categories", "tags", "description")
ALLOWED_CATEGORIES = {
    ("Learning", "AI Engineering"),
    ("Projects", "AI Engineering"),
    ("Projects", "Performance"),
    ("LLM Evaluation", "Methodology"),
    ("LLM Evaluation", "System Build"),
    ("LLM Evaluation", "Live Run"),
    ("LLM Evaluation", "Reliability"),
}
FORBIDDEN_LITERAL = ("우태강", "김형국", "장영원", "조대협", "황대민")
FORBIDDEN_PATTERN = (
    r'sk-[A-Za-z0-9]{16,}', r'sk-ant-[A-Za-z0-9-]{16,}', r'sk-or-v1-[A-Za-z0-9]{16,}',
    r'ghp_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}',
    r'ntn_[A-Za-z0-9]{20,}', r'AKIA[0-9A-Z]{16}', r'AIza[0-9A-Za-z_-]{20,}',
)
PLACEHOLDER_PATTERNS = (
    r'^date:\s*YYYY-MM-DD',
    r'^categories:\s*\[대분류',
    r'^tags:\s*\[소문자',
    r'https?://(?:1차-출처-)?URL\b',
    r'\(여기서[^)]*\)',
    r'^```language\s*$',
    r'<!--\s*(?:훅|이 템플릿을)',
)
STYLE_PATTERNS = {
    r'이번 (?:글|포스트)에서는': "state the result or problem directly",
    r'오늘은 .{0,40}(?:알아보|살펴보)': "remove presenter-style opening",
    r'단순히? .{0,50}(?:아니라|넘어)': "replace contrast cliché with a concrete claim",
    r'결론적으로': "state the conclusion without a transition cliché",
    r'(?:혁신적|획기적|압도적|완벽하게)': "replace promotional adjective with evidence",
}


def parse_front_matter(text: str) -> tuple[dict, int, list[str]]:
    match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', text, re.S)
    if not match:
        return {}, 0, ["front matter missing"]
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return {}, match.end(), [f"invalid YAML: {exc}"]
    if not isinstance(data, dict):
        return {}, match.end(), ["front matter must be a YAML mapping"]
    return data, match.end(), []


def _plain_prose(text: str) -> str:
    text = re.sub(r'```.*?```|~~~.*?~~~', '', text, flags=re.S)
    text = re.sub(r'^\[\^[^\]]+\]:.*(?:\n(?: {2,}|\t).*)*', '', text, flags=re.M)
    text = re.sub(r'`[^`\n]+`|<[^>]+>|!?\[[^\]]*\]\([^)]*\)', '', text)
    return text


def _without_footnote_definitions(text: str) -> str:
    """Remove complete footnote definition blocks while keeping inline refs."""
    output: list[str] = []
    in_definition = False
    for line in text.splitlines(keepends=True):
        if re.match(r'^\[\^[^\]]+\]:', line):
            in_definition = True
            continue
        if in_definition and (not line.strip() or re.match(r'^(?: {2,}|\t)', line)):
            continue
        in_definition = False
        output.append(line)
    return ''.join(output)


def check_post(
    path: str | os.PathLike[str],
    slugs: set[str],
    assets_root: str | os.PathLike[str],
    *,
    now: dt.datetime | None = None,
    strict_style: bool = False,
) -> tuple[list[str], list[str], dict]:
    post_path = Path(path)
    text = post_path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    front, body_start, front_errors = parse_front_matter(text)
    errors.extend(front_errors)
    body = text[body_start:]

    for field in REQUIRED_FIELDS:
        if field not in front or front[field] in (None, "", []):
            errors.append(f"required front matter field missing or empty: {field}")

    title = front.get("title")
    description = front.get("description")
    if title is not None and not isinstance(title, str):
        errors.append("title must be a string")
    if description is not None and not isinstance(description, str):
        errors.append("description must be a string")

    categories = front.get("categories")
    if not isinstance(categories, list) or not all(isinstance(value, str) for value in categories):
        errors.append("categories must be a list of strings")
    elif tuple(categories) not in ALLOWED_CATEGORIES:
        errors.append(f"unsupported category pair: {categories}")

    tags = front.get("tags")
    if not isinstance(tags, list) or not tags or not all(isinstance(value, str) and value for value in tags):
        errors.append("tags must be a non-empty list of strings")

    published = front.get("date")
    if isinstance(published, str):
        try:
            published = dt.datetime.strptime(published, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            published = None
    if not isinstance(published, dt.datetime):
        errors.append("date must include a time and UTC offset, for example 2026-07-22 09:00:00 +0900")
    elif published.tzinfo is None or published.utcoffset() is None:
        errors.append("date must be timezone-aware")
    else:
        current = now or dt.datetime.now(dt.timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if published.astimezone(dt.timezone.utc) > current.astimezone(dt.timezone.utc):
            errors.append(f"future publication date: {published.isoformat()}")
        filename_date = re.match(r'^(\d{4}-\d{2}-\d{2})-', post_path.name)
        if filename_date and published.date().isoformat() != filename_date.group(1):
            errors.append("filename date and front matter date differ")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, re.M | re.I):
            errors.append(f"template placeholder remains: {pattern}")

    references = set(re.findall(r'\[\^([^\]]+)\]', _without_footnote_definitions(text)))
    definitions = set(re.findall(r'^\[\^([^\]]+)\]:', text, re.M))
    if references - definitions:
        errors.append(f"undefined footnotes: {sorted(references - definitions)}")
    if definitions - references:
        warnings.append(f"unused footnotes: {sorted(definitions - references)}")

    for link in re.findall(r'\]\((/posts/[^)]+/)\)', text):
        slug = link.strip('/').split('/')[-1]
        if slug not in slugs:
            errors.append(f"broken internal post link: {link}")
    root = Path(assets_root)
    for image in re.findall(r'\]\((/assets/[^)]+)\)', text):
        if not (root / image.lstrip('/')).exists():
            errors.append(f"missing asset: {image}")

    opened = text.count('<span class="term"')
    closed = len(re.findall(r'<span class="term" data-tip="[^"]*">[^<]+</span>', text))
    if opened != closed:
        errors.append(f"unbalanced tooltip spans: {opened}!={closed}")
    if re.search(r'data-tip="[^"]*data-tip', text):
        errors.append("nested tooltip data-tip")

    for literal in FORBIDDEN_LITERAL:
        if literal in text:
            errors.append(f"forbidden literal: {literal}")
    for pattern in FORBIDDEN_PATTERN:
        if re.search(pattern, text):
            errors.append(f"possible secret matches: {pattern}")

    prose = _plain_prose(body)
    if re.search(r'멘토(?!링|님)', prose):
        warnings.append('review "멘토" honorific usage')
    for pattern, message in STYLE_PATTERNS.items():
        if re.search(pattern, prose):
            target = errors if strict_style else warnings
            target.append(f"style: {message} ({pattern})")

    in_fence = False
    fence_char = ""
    for line_number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            char = marker.group(1)[0]
            if not in_fence:
                in_fence, fence_char = True, char
            elif char == fence_char:
                in_fence = False
            continue
        if in_fence or line.startswith(("|", "[^", "!", ">", "#", "_")):
            continue
        plain = re.sub(r'<[^>]+>', '', line)
        for sentence in re.split(r'(?<=[다요][.!?])\s|(?<=[.!?])\s+(?=[A-Z가-힣])', plain):
            if len(sentence) > 160:
                warnings.append(f"L{line_number}: long sentence ({len(sentence)} characters)")
                break
    return errors, warnings, front


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_root")
    parser.add_argument("--post", help="validate one filename")
    parser.add_argument("--strict-style", action="store_true")
    args = parser.parse_args()

    site_root = Path(args.site_root)
    posts_dir = site_root / "_posts"
    if not posts_dir.is_dir():
        parser.error(f"posts directory not found: {posts_dir}")
    slugs = {path.name[11:-3] for path in posts_dir.glob("*.md")}
    files = [posts_dir / args.post] if args.post else sorted(posts_dir.glob("*.md"))
    if args.post and not files[0].is_file():
        parser.error(f"post not found: {files[0]}")

    failed = False
    pinned: list[str] = []
    for path in files:
        errors, warnings, front = check_post(
            path, slugs, site_root, strict_style=args.strict_style
        )
        if front.get("pin") is True:
            pinned.append(path.name)
        failed = failed or bool(errors)
        print(("FAIL" if errors else "OK") + f" {path.name}")
        for error in errors:
            print(f"  ERROR {error}")
        for warning in warnings:
            print(f"  WARN  {warning}")
    if not args.post and len(pinned) > 1:
        failed = True
        print(f"ERROR multiple pinned posts: {pinned}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
