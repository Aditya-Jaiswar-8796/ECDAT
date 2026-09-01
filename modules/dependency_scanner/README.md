# Dependency Scanner

Member 4 module for parsing dependency manifest files and identifying
cryptographically relevant dependencies.

## Supported Formats

| File | Parser | Sections scanned |
|---|---|---|
| `package.json` | `package_json.py` | dependencies, devDependencies, peerDependencies, optionalDependencies, bundleDependencies |
| `requirements.txt` | `requirements_txt.py` | all requirement lines |
| `pom.xml` | `pom_xml.py` | `<dependencies>` and `<dependencyManagement>` |

## Usage

```python
from modules.dependency_scanner.scanner import scan_dependencies

# Scan a directory (auto-detects all three manifest types)
result = scan_dependencies("path/to/project")

# Scan a single manifest
from modules.dependency_scanner import package_json
result = package_json.parse_package_json("path/to/package.json")
```

## Output

Each parser returns a `ParseResult` with:
- `dependencies`: list of `DependencyFinding`
- `errors`: non-fatal parse errors (missing/malformed files)
- `success`: whether the file parsed cleanly

Each `DependencyFinding` contains:
- `name` - dependency name
- `version` - version (or `*` if unpinned, or template like `${spring.version}`)
- `manifest_path` / `manifest_type` - source tracking
- `section` - which manifest section contained it
- `crypto_relevance` - `CryptoRelevance` object (relevance flag, confidence,
  reasons, crypto category)
- `raw_entry` - original manifest line for evidence

## Safety

- Missing files → reported as errors, never raise
- Malformed JSON/XML → reported as errors, parsing continues for other files
- Comments, blank lines, pip options, environment markers handled
- Dependencies without pinned versions handled gracefully
- No dependency findings are invented - only what is actually in the manifest

## Crypto Relevance

`crypto_relevance.py` classifies dependencies using:
1. A curated database of known crypto packages (per ecosystem)
2. Keyword heuristics on the package name/description

Each match records a confidence (`high`/`medium`/`low`) and a category such
as `encryption`, `tls`, `signing`, or `hashing`, plus human-readable reasons
that serve as evidence for downstream consumers.