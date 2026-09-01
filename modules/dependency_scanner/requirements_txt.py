"""Python requirements.txt dependency manifest parser.

Parses pip-style requirements.txt files including:
- Standard pinning (package==1.0.0)
- Compatible release (package~=1.0)
- Greater/less than (package>=1.0, package<=2.0)
- Environment markers (package==1.0; python_version>="3.6")
- Comments and blank lines
- Inline comments
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .crypto_relevance import CryptoRelevance, check_crypto_relevance


@dataclass
class DependencyFinding:
    """A single dependency discovered in a requirements.txt file."""
    name: str
    version: str
    manifest_path: str
    manifest_type: str
    section: str  # always "requirements" for requirements.txt
    extras: Optional[str] = None  # e.g. [security,dev]
    environment_marker: Optional[str] = None  # e.g. python_version>="3.6"
    crypto_relevance: Optional[CryptoRelevance] = None
    raw_entry: Optional[str] = None
    parse_errors: List[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """Result of parsing a requirements.txt file."""
    manifest_path: str
    manifest_type: str
    dependencies: List[DependencyFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True


# Regex for parsing a requirement line
# Matches: package_name[extras]>=version;marker  # inline comment
_REQUIREMENT_RE = re.compile(
    r"^\s*"
    r"(?P<name>[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"  # package name
    r"(?:\[(?P<extras>[^\]]+)\])?"  # optional extras like [security]
    r"(?P<version>[>=<~!]=?[^;#\s]*)?"  # version specifier
    r"(?:\s*;\s*(?P<marker>[^\s#]+(?:\s*[^\s#]+)*))?"  # environment marker
    r""  # end
)

# Patterns that indicate this is NOT a requirement line
_SKIP_PATTERNS = [
    re.compile(r"^\s*#"),       # full-line comment
    re.compile(r"^\s*$"),       # blank line
    re.compile(r"^\s*-"),       # pip options like -r, -e, --index-url
    re.compile(r"^\s*https?://"),  # direct URL without -r
]


def parse_requirements_txt(file_path: str, check_crypto: bool = True) -> ParseResult:
    """Parse a requirements.txt file and extract all dependencies.

    Safely handles comments, blank lines, pip options, inline comments,
    and malformed lines.

    Args:
        file_path: Path to the requirements.txt file.
        check_crypto: Whether to evaluate cryptographic relevance.

    Returns:
        ParseResult with discovered dependencies and any errors encountered.
    """
    result = ParseResult(
        manifest_path=file_path,
        manifest_type="requirements.txt",
    )

    # Handle missing file
    if not os.path.exists(file_path):
        result.success = False
        result.errors.append(f"File not found: {file_path}")
        return result

    # Read file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, IOError) as e:
        result.success = False
        result.errors.append(f"Failed to read file: {e}")
        return result

    if not content.strip():
        # Empty file is valid but has no dependencies
        return result

    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Strip inline comments (but be careful with URLs containing #)
        # Only strip comments that appear after package specifiers
        comment_stripped = _strip_inline_comment(stripped)

        # Skip non-requirement lines
        if _should_skip(comment_stripped):
            continue

        # Try to parse as a requirement
        finding = _parse_requirement_line(
            comment_stripped, file_path, line_num
        )
        if finding is None:
            # Could not parse - record as a soft error
            if comment_stripped and not comment_stripped.startswith("-"):
                result.errors.append(
                    f"Line {line_num}: Could not parse requirement: {stripped}"
                )
            continue

        # Evaluate cryptographic relevance
        if check_crypto:
            finding.crypto_relevance = check_crypto_relevance(finding.name)

        result.dependencies.append(finding)

    return result


def _strip_inline_comment(line: str) -> str:
    """Remove inline comments from a requirement line.

    Comments start with # that is not inside a version specifier.
    """
    # Find # that is not inside brackets or quotes
    in_bracket = False
    for i, ch in enumerate(line):
        if ch == "[":
            in_bracket = True
        elif ch == "]":
            in_bracket = False
        elif ch == "#" and not in_bracket:
            return line[:i].strip()
    return line


def _should_skip(line: str) -> bool:
    """Check if a line should be skipped during parsing."""
    for pattern in _SKIP_PATTERNS:
        if pattern.match(line):
            return True
    return False


def _parse_requirement_line(
    line: str, file_path: str, line_num: int
) -> Optional[DependencyFinding]:
    """Parse a single requirement line into a DependencyFinding.

    Returns None if the line cannot be parsed.
    """
    if not line:
        return None

    match = _REQUIREMENT_RE.match(line)
    if not match:
        return None

    name = match.group("name")
    if not name:
        return None

    extras = match.group("extras")
    version = match.group("version") or "*"
    marker = match.group("marker")

    # Build a clean version string
    version_str = version.strip() if version else "*"

    # Include extras in version for clarity (e.g. "cryptography[vs2017]>=2.3")
    display_version = version_str
    if extras:
        display_version = f"[{extras}]{version_str}"

    return DependencyFinding(
        name=name.strip(),
        version=version_str,
        manifest_path=file_path,
        manifest_type="requirements.txt",
        section="requirements",
        extras=extras,
        environment_marker=marker.strip() if marker else None,
        raw_entry=line,
    )
