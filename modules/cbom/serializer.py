"""CBOM document serializer.

Serializes CBOMDocument objects to JSON format for consumption
by the backend API (Member 1) and dashboard views (Member 6).
"""

import json
from dataclasses import asdict
from typing import Any, Dict, Optional

from .generator import CBOMDocument, CBOMEntry


def serialize_to_json(
    cbom_doc: CBOMDocument,
    indent: int = 2,
    include_metadata: bool = True,
) -> str:
    """Serialize a CBOMDocument to a JSON string.

    Args:
        cbom_doc: The CBOM document to serialize.
        indent: JSON indentation level (2 for readable, 0 for compact).
        include_metadata: Whether to include scan metadata and errors.

    Returns:
        JSON string representation of the CBOM document.
    """
    output = {
        "format_version": cbom_doc.format_version,
        "tool_version": cbom_doc.tool_version,
        "generated_at": cbom_doc.generated_at,
        "project_path": cbom_doc.project_path,
        "summary": {
            "total_dependencies": cbom_doc.total_dependencies,
            "crypto_relevant_count": cbom_doc.crypto_relevant_count,
            "certificate_count": cbom_doc.certificate_count,
            "total_entries": len(cbom_doc.entries),
        },
        "entries": [_entry_to_dict(entry) for entry in cbom_doc.entries],
    }

    if include_metadata:
        output["scan_errors"] = cbom_doc.scan_errors
        output["metadata"] = cbom_doc.metadata

    return json.dumps(output, indent=indent, default=str)


def serialize_to_dict(cbom_doc: CBOMDocument) -> Dict[str, Any]:
    """Serialize a CBOMDocument to a Python dictionary.

    Useful for direct integration with FastAPI response models (Member 1)
    without the overhead of JSON serialization/deserialization.

    Args:
        cbom_doc: The CBOM document to serialize.

    Returns:
        Dictionary representation of the CBOM document.
    """
    return {
        "format_version": cbom_doc.format_version,
        "tool_version": cbom_doc.tool_version,
        "generated_at": cbom_doc.generated_at,
        "project_path": cbom_doc.project_path,
        "summary": {
            "total_dependencies": cbom_doc.total_dependencies,
            "crypto_relevant_count": cbom_doc.crypto_relevant_count,
            "certificate_count": cbom_doc.certificate_count,
            "total_entries": len(cbom_doc.entries),
        },
        "entries": [_entry_to_dict(entry) for entry in cbom_doc.entries],
        "scan_errors": cbom_doc.scan_errors,
        "metadata": cbom_doc.metadata,
    }


def save_cbom_json(
    cbom_doc: CBOMDocument,
    output_path: str,
    indent: int = 2,
) -> str:
    """Serialize and save a CBOM document to a JSON file.

    Args:
        cbom_doc: The CBOM document to save.
        output_path: Path where the JSON file should be written.
        indent: JSON indentation level.

    Returns:
        The output file path on success.
    """
    json_str = serialize_to_json(cbom_doc, indent=indent)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    return output_path


def _entry_to_dict(entry: CBOMEntry) -> Dict[str, Any]:
    """Convert a CBOMEntry to a plain dictionary."""
    return {
        "id": entry.id,
        "type": entry.type,
        "name": entry.name,
        "version": entry.version,
        "source_manifest": entry.source_manifest,
        "manifest_type": entry.manifest_type,
        "section": entry.section,
        "crypto_relevance": entry.crypto_relevance,
        "crypto_category": entry.crypto_category,
        "evidence": entry.evidence,
        "metadata": entry.metadata,
    }
