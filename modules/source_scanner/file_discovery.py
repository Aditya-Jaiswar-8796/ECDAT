from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

IGNORED_DIRS: set[str] = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".next",
    "target",
}

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".java": "java",
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


def is_ignored_directory(dirname: str) -> bool:
    return dirname in IGNORED_DIRS


def is_supported_extension(filename: str) -> bool:
    ext = os.path.splitext(filename)[1]
    return ext in EXTENSION_TO_LANGUAGE


def detect_language(file_path: str) -> Optional[str]:
    ext = os.path.splitext(file_path)[1]
    return EXTENSION_TO_LANGUAGE.get(ext)


def discover_source_files(root_dir: str) -> List[str]:
    root = Path(root_dir)

    if not root.exists():
        raise FileNotFoundError(f"Scan root directory does not exist: {root_dir}")

    discovered: List[str] = []

    for current_dir, subdirs, files in os.walk(root):
        subdirs[:] = [
            name
            for name in subdirs
            if not is_ignored_directory(name)
        ]

        for filename in files:
            if is_supported_extension(filename):
                full_path = os.path.join(current_dir, filename).replace("\\", "/")
                discovered.append(full_path)

    discovered.sort()
    return discovered