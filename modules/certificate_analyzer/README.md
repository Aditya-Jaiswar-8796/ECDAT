# Certificate Analyzer

Member 4 module for extracting public metadata from PEM/X.509 certificate
files. This is a **secondary (P2)** feature implemented after dependency
scanning and CBOM generation were complete.

## Usage

```python
from modules.certificate_analyzer.analyzer import (
    analyze_certificate_file,
    analyze_certificate_directory,
)

# Single file
finding = analyze_certificate_file("certs/server.crt")

# Directory (scans *.pem, *.crt, *.cer, *.cert, *.der)
findings = analyze_certificate_directory("certs/")
```

## Extracted Public Metadata

- `subject` / `issuer` (as `commonName=..., organizationName=...` text)
- `serial_number`
- `not_before` / `not_after` (validity window)
- `signature_algorithm` (e.g. `sha256WithRSAEncryption`)
- `key_type` and `key_size` (e.g. `rsaEncryption`, 2048)
- `san_dns_names` (subject alternative names, DNS type)
- `is_expired`, `is_self_signed`
- `parse_errors` for anything that could not be analyzed

## Safety Guarantees

- **Private keys are NEVER analyzed.** Files containing
  `-----BEGIN ... PRIVATE KEY-----` blocks are rejected immediately.
- Only public certificate metadata is extracted.
- Private key material is never stored, displayed, logged, or emitted
  into CBOM output.
- Invalid or malformed certificate files produce a finding with a
  `parse_errors` list instead of raising.

## Implementation Notes

Uses only the Python standard library. Decoding is done with a minimal
self-contained ASN.1/DER parser so the module works across Python versions
and builds (including Python 3.14, where older cert could not be decoded
by the internal `ssl._ssl._test_decode_cert` path).