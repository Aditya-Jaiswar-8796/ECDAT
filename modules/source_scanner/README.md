# ECDAT Source-Code Scanner (Member 3)

A safe **static** source-code scanner that discovers cryptographic usage in
source code and produces normalized findings that are compatible with the
canonical **CryptoAsset** contract maintained by Member 1.

## Security guarantee

- The scanner is **static analysis only**. It reads source files as plain text
  and **never imports, executes, or runs** the scanned code.
- Malformed/unreadable files are handled safely: a bad file produces no
  findings (or best-effort partial findings) and never stops the whole scan.
- Ignored directories are skipped entirely: `.git`, `node_modules`, `build`,
  `dist`, `__pycache__`, `.next`, `target`.

## Supported languages

| Language      | Detector file              | What it detects                                                      |
| ------------- | -------------------------- | -------------------------------------------------------------------- |
| Java          | `detectors/java.py`        | `javax.crypto` & `java.security`: Cipher, MessageDigest, KeyPairGenerator, KeyGenerator, SecretKeyFactory, Mac, Signature, SecureRandom, KeyStore, KeyAgreement |
| Python        | `detectors/python.py`      | `hashlib` (sha*/md5/new/pbkdf2_hmac), `hmac`, `os.urandom`, `secrets`, `cryptography.fernet` |
| JavaScript    | `detectors/javascript.py`  | Node `crypto` module (createHash, createCipheriv, createHmac, ...), Web Crypto `crypto.subtle` |
| TypeScript    | `detectors/javascript.py`  | Same surfaces as JavaScript; findings are tagged `language: typescript` |

## Scanner pipeline

```
1. Recursive file discovery        -> file_discovery.discover_source_files
2. Safe filtering                  -> file_discovery.IGNORED_DIRS
3. Language detection              -> file_discovery.detect_language (by extension)
4. Crypto API/pattern detection    -> language detector (regex/substring based)
5. Evidence extraction             -> labelled source snippet around the match
6. Line number extraction          -> 1-based line of the matched call
7. Confidence assignment           -> HIGH / MEDIUM / LOW (detection quality only)
8. Normalized CryptoAsset findings -> detectors/base.make_finding
```

## Quick start

```python
from modules.source_scanner.scanner import scan, scan_directory

# Scan a whole directory tree
result = scan_directory("demo_repository")
for finding in result["findings"]:
    print(finding["language"], finding["api"], finding["line_number"], finding["confidence"])

# Scan a single file
result = scan("demo_repository/java/PaymentService.java")
```

## Findings / CryptoAsset contract

Every finding is a dict with the canonical CryptoAsset keys. Scanner fills only
the **discovery** fields; all downstream fields stay `None` because risk,
Mosca assessment, migration priority and recommendations belong to Members 1
and 2:

```
id, algorithm, operation, key_size, language, library, api,
file_path, line_number, evidence, confidence,              <- filled by scanner
business_criticality, data_lifetime_years, internet_exposure,
migration_complexity, risk_score, risk_level, migration_priority,
mosca_assessment, recommendation                            <- left as None
```

## Confidence rules

- **HIGH** – clear crypto API call with an identifiable algorithm
  (e.g. `Cipher.getInstance("RSA/ECB/OAEP...")`)
- **MEDIUM** – likely crypto usage but algorithm/operation incomplete
  (e.g. `os.urandom`, `hmac.new` without extracted algorithm)
- **LOW** – weak signal needing downstream review
  (e.g. a bare `import * as crypto from "crypto"`)

## Running the tests

```bash
python -m unittest discover -s tests -v
```

or, if you have pytest:

```bash
python -m pytest tests/test_source_scanner.py -v
```

## Ownership / integration

- **Member 1** consumes the normalized findings (`scan_directory` output)
  and assigns IDs + downstream fields.
- **Member 2** reviews the algorithm → operation mappings and owns the final
  cryptographic security classification. Where a mapping is uncertain the
  scanner keeps the raw evidence so Member 2 can inspect it.