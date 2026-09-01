# CBOM (Cryptographic Bill of Materials)

Member 4 module that transforms dependency scanning and certificate analysis
findings into a clean, traceable CBOM-style JSON document.

> **Note:** This is a hackathon prototype CBOM, not a full enterprise CBOM
> implementation. It does not claim full compliance with any CBOM standard.

## Usage

```python
from modules.dependency_scanner.scanner import scan_dependencies
from modules.cbom.generator import generate_cbom
from modules.cbom.serializer import serialize_to_json, save_cbom_json

# 1. Scan dependencies
scan = scan_dependencies("path/to/project")

# 2. (Optional) certificate findings
cert_findings = [...]  # list of dicts from the certificate analyzer

# 3. Generate CBOM from REAL findings
cbom = generate_cbom(scan, certificate_findings=cert_findings)

# 4. Serialize
json_str = serialize_to_json(cbom)
save_cbom_json(cbom, "cbom.json")
```

## CBOM JSON Structure

```json
{
  "format_version": "1.0.0",
  "tool_version": "0.1.0-hackathon",
  "generated_at": "2026-09-02T00:00:00+00:00",
  "project_path": "path/to/project",
  "summary": {
    "total_dependencies": 27,
    "crypto_relevant_count": 17,
    "certificate_count": 1,
    "total_entries": 28
  },
  "entries": [
    {
      "id": "6afce8881b02",
      "type": "dependency",
      "name": "crypto-js",
      "version": "^4.1.1",
      "source_manifest": ".../package.json",
      "manifest_type": "package.json",
      "section": "dependencies",
      "crypto_relevance": "high",
      "crypto_category": "encryption",
      "evidence": {
        "manifest_path": ".../package.json",
        "manifest_type": "package.json",
        "section": "dependencies",
        "raw_entry": "\"crypto-js\": \"^4.1.1\"",
        "crypto_reasons": ["Known cryptographic package: crypto-js", "..."]
      },
      "metadata": {}
    }
  ],
  "scan_errors": [],
  "metadata": {}
}
```

## Traceability

Every CBOM entry carries an `evidence` block that lets consumers trace it
back to its source finding:

- `manifest_path` - where the dependency/certificate came from
- `manifest_type` - which manifest (package.json / requirements.txt / pom.xml)
- `section` - which section/scope contained it
- `raw_entry` - the original manifest line/entry
- `crypto_reasons` - why it was considered crypto-relevant

The `id` field is a deterministic hash of `manifest + name + version`, so
the same finding always produces the same ID.

## Serializers

- `serialize_to_json(doc)` → pretty-printed JSON string
- `serialize_to_dict(doc)` → plain dict (for FastAPI response models)
- `save_cbom_json(doc, path)` → writes JSON to a file

## Consumer Notes

For **Member 1** (FastAPI/SQLite): use `serialize_to_dict()` directly, or
parse the JSON string. The `id`, `type`, `name`, `version`, `crypto_*` and
`evidence` fields map naturally to a DB row per entry.

For **Member 6** (dashboard/reports): display `summary.*` for aggregate
charts and iterate `entries` for detail views, highlighting entries where
`crypto_relevance` is `high`/`medium`.