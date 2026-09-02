from __future__ import annotations

from typing import List, Optional


def read_source_lines(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def find_line_number(file_path: str, needle: str) -> Optional[int]:
    for index, line in enumerate(read_source_lines(file_path)):
        if needle in line:
            return index + 1
    return None


def extract_evidence_line(file_path: str, line_number: int) -> Optional[str]:
    lines = read_source_lines(file_path)
    if line_number < 1 or line_number > len(lines):
        return None
    return lines[line_number - 1]


def build_snippet(
    lines: List[str],
    line_number: int,
    context_lines: int = 1,
) -> Optional[str]:
    if not lines or line_number < 1 or line_number > len(lines):
        return None

    start = max(1, line_number - context_lines)
    end = min(len(lines), line_number + context_lines)

    snippet_lines: List[str] = []
    for idx in range(start, end + 1):
        snippet_lines.append(f"{idx}: {lines[idx - 1]}")

    return "\n".join(snippet_lines)


def extract_evidence_block(
    file_path: str,
    line_number: int,
    context_lines: int = 1,
) -> Optional[str]:
    lines = read_source_lines(file_path)
    return build_snippet(lines, line_number, context_lines)


def extract_arguments(line_text: str, call_name: str) -> Optional[str]:
    import re

    pattern = re.escape(call_name) + r"\s*\(\s*(.*?)\s*\)"
    match = re.search(pattern, line_text)
    if match:
        return match.group(1)
    return None


def clean_algorithm_text(raw: str) -> Optional[str]:
    if not raw:
        return None
    cleaned = raw.strip().strip("\"'")
    cleaned = cleaned.strip().rstrip(",).")
    if not cleaned:
        return None
    return cleaned