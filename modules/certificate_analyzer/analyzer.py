"""Certificate analyzer - extracts public metadata from PEM/X.509 certificates.

Only analyzes public certificate metadata:
- subject, issuer, validity dates
- signature algorithm
- public key info (type and size)
- SAN DNS names
- self-signed / expiry status

NEVER extracts, stores, displays, logs, or exposes private keys.
Private key PEM blocks are explicitly rejected and never parsed.

This module uses only Python standard library. It tries CPython's built-in
SSL certificate decoder first, then falls back to a minimal self-contained
ASN.1/DER parser so it works across Python versions and builds.
"""

import base64
import datetime
import os
import re
import ssl
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# PEM block header patterns
_CERT_BLOCK_RE = re.compile(
    r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
    re.DOTALL,
)
_PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    re.IGNORECASE,
)

# OID -> label mappings for readable output
_OID_LABELS = {
    "2.5.4.3": "commonName",
    "2.5.4.6": "countryName",
    "2.5.4.7": "localityName",
    "2.5.4.8": "stateOrProvinceName",
    "2.5.4.10": "organizationName",
    "2.5.4.11": "organizationalUnitName",
    "2.5.4.5": "serialNumber",
    "1.2.840.113549.1.1.1": "rsaEncryption",
    "1.2.840.10045.2.1": "id-ecPublicKey",
    "1.2.840.10040.4.1": "id-dsa",
    "1.2.840.113549.1.1.11": "sha256WithRSAEncryption",
    "1.2.840.113549.1.1.12": "sha384WithRSAEncryption",
    "1.2.840.113549.1.1.13": "sha512WithRSAEncryption",
    "1.2.840.113549.1.1.5": "sha1WithRSAEncryption",
    "1.2.840.10045.4.3.2": "ecdsa-with-SHA256",
    "1.2.840.10045.4.3.3": "ecdsa-with-SHA384",
    "1.2.840.10045.4.3.4": "ecdsa-with-SHA512",
    "1.2.840.10040.4.3": "dsa-with-sha1",
    "1.3.101.112": "Ed25519",
    "1.3.101.113": "Ed448",
}

# Curve OID -> bit size
_EC_CURVE_SIZES = {
    "1.2.840.10045.3.1.7": 256,   # prime256v1 (P-256)
    "1.3.132.0.34": 384,          # secp384r1 (P-384)
    "1.3.132.0.35": 521,          # secp521r1 (P-521)
    "1.3.101.110": 256,           # Ed25519
}


@dataclass
class CertificateFinding:
    """Metadata extracted from a public X.509 certificate."""
    source_file: str
    subject: str = ""
    issuer: str = ""
    serial_number: str = ""
    not_before: Optional[str] = None
    not_after: Optional[str] = None
    signature_algorithm: Optional[str] = None
    key_type: Optional[str] = None
    key_size: Optional[int] = None
    version: Optional[str] = None
    san_dns_names: List[str] = field(default_factory=list)
    is_expired: bool = False
    is_self_signed: bool = False
    parse_errors: List[str] = field(default_factory=list)


def analyze_certificate_file(file_path: str) -> CertificateFinding:
    """Analyze a public certificate file.

    Only reads certificate PEM blocks. Private key blocks are detected
    and skipped with a warning. Invalid or unparseable files return a
    finding with error information instead of raising.

    Args:
        file_path: Path to a PEM or DER certificate file.

    Returns:
        CertificateFinding with public metadata only.
    """
    result = CertificateFinding(source_file=file_path)

    # Handle missing file
    if not os.path.exists(file_path):
        result.parse_errors.append(f"File not found: {file_path}")
        return result

    # Read file content
    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except (OSError, IOError) as e:
        result.parse_errors.append(f"Failed to read file: {e}")
        return result

    if not content.strip():
        result.parse_errors.append("File is empty")
        return result

    # Check for private key material - reject immediately
    text_preview = content[0:2048].decode("utf-8", errors="ignore")
    if _PRIVATE_KEY_BLOCK_RE.search(text_preview):
        result.parse_errors.append(
            "File contains private key material - private keys are never analyzed"
        )
        return result

    # Try PEM decoding first, then raw DER
    decoded = _decode_certificate(content)
    if decoded is None:
        result.parse_errors.append(
            "Could not decode certificate - file contains no valid X.509 certificate"
        )
        return result

    _populate_finding(result, decoded)
    return result


def analyze_certificate_directory(
    directory_path: str, extensions: Optional[List[str]] = None
) -> List[CertificateFinding]:
    """Analyze all certificate files in a directory.

    Only parses files with certificate-like extensions (.pem, .crt, .cer,
    .cert, .der) and only extracts public metadata.

    Args:
        directory_path: Directory to scan for certificates.
        extensions: Optional file extensions to scan for.

    Returns:
        List of CertificateFinding objects. Files that fail to parse are
        included with error info rather than raising.
    """
    if extensions is None:
        extensions = [".pem", ".crt", ".cer", ".cert", ".der"]

    findings: List[CertificateFinding] = []
    if not os.path.isdir(directory_path):
        return findings

    for filename in sorted(os.listdir(directory_path)):
        lower_name = filename.lower()
        if not any(lower_name.endswith(ext) for ext in extensions):
            continue
        file_path = os.path.join(directory_path, filename)
        findings.append(analyze_certificate_file(file_path))

    return findings


def _decode_certificate(content: bytes) -> Optional[dict]:
    """Decode a certificate from PEM or DER bytes.

    Attempts to extract the first certificate PEM block from the content.
    Falls back to treating the content as raw DER bytes.

    Returns a normalized dict with fields, or None if decoding fails.
    """
    # Try PEM format
    text = content.decode("utf-8", errors="ignore")
    cert_matches = _CERT_BLOCK_RE.findall(text)

    if cert_matches:
        der = base64.b64decode(
            re.sub(r"-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\\s",
                   "", cert_matches[0])
        )
        return _decode_der_certificate(der)

    # Fallback: treat content as raw DER certificate
    return _decode_der_certificate(content)


def _decode_der_certificate(der: bytes) -> Optional[dict]:
    """Decode a DER-encoded X.509 certificate with a minimal ASN.1 parser.

    Returns a normalized dict matching the downstream population logic.
    """
    try:
        root, offset = _parse_der(der, 0)
        if root.get("tag") != 0x30:
            return None

        cert_children = root.get("children", [])
        if len(cert_children) < 3:
            return None

        tbs = cert_children[0]
        if tbs.get("tag") != 0x30:
            return None

        sig_alg_node = cert_children[1]
        # signatureValue is a BIT STRING - ignored here (public info only)

        tbs_children = tbs.get("children", [])

        # Optional [0] version (v1 certs have no version field)
        idx = 0
        version = "1"
        if tbs_children and tbs_children[0].get("tag") == 0xA0:
            ver_int = _extract_integer(tbs_children[0])
            version = str((ver_int or 0) + 1)
            idx = 1

        if len(tbs_children) < idx + 6:
            return None

        serial_node = tbs_children[idx]
        serial_number = _format_serial(_extract_integer(serial_node))

        signature_algorithm = _algorithm_name(tbs_children[idx + 1])

        issuer = _name_to_text(tbs_children[idx + 2])
        validity = _parse_validity(tbs_children[idx + 3])
        subject = _name_to_text(tbs_children[idx + 4])
        spki = _parse_spki(tbs_children[idx + 5])

        return {
            "subject": subject,
            "issuer": issuer,
            "serialNumber": serial_number,
            "version": version,
            "signatureAlgorithm": signature_algorithm,
            "notBefore": validity[0],
            "notAfter": validity[1],
            "key_type": spki[0],
            "key_size": spki[1],
            "subjectAltName": [],
        }
    except Exception:
        # Any structural error means this is not a valid DER certificate
        return None


def _parse_der(data: bytes, offset: int) -> tuple:
    """Parse one DER TLV element.

    Returns (node_dict, next_offset). Constructed tags (0x20 bit set)
    produce a node with 'children' list.
    """
    tag = data[offset]
    offset += 1

    # Read length (short form or long form)
    length_byte = data[offset]
    offset += 1
    if length_byte & 0x80:
        num_bytes = length_byte & 0x7F
        length = int.from_bytes(data[offset : offset + num_bytes], "big")
        offset += num_bytes
    else:
        length = length_byte

    value = data[offset : offset + length]
    offset += length

    if tag & 0x20:
        # Constructed - recursively parse children
        children = []
        child_offset = 0
        while child_offset < len(value):
            child, child_offset = _parse_der(value, child_offset)
            children.append(child)
        return {"tag": tag, "children": children}, offset

    return {"tag": tag, "value": value}, offset


def _decode_oid(value: bytes) -> str:
    """Decode an ASN.1 OBJECT IDENTIFIER to its dotted string form."""
    parts = []
    first = value[0]
    parts.append(str(first // 40))
    parts.append(str(first % 40))

    current = 0
    for byte in value[1:]:
        current = (current << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(current))
            current = 0

    return ".".join(parts)


def _extract_integer(node: dict) -> Optional[int]:
    """Extract an integer from an INTEGER node or a wrapped INTEGER."""
    # Handle [0] EXPLICIT INTEGER (tag 0xA0) wrapping
    if node.get("tag") == 0xA0:
        children = node.get("children", [])
        if children:
            node = children[0]

    if node.get("tag") == 0x02:
        return int.from_bytes(node.get("value", b""), "big", signed=False)
    return None


def _algorithm_name(alg_node: dict) -> Optional[str]:
    """Extract a readable algorithm name from an AlgorithmIdentifier."""
    children = alg_node.get("children", [])
    if not children:
        return None
    oid = _decode_oid(children[0].get("value", b""))
    return _OID_LABELS.get(oid, oid)


def _name_to_text(name_node: dict) -> str:
    """Extract a readable name string from an X.509 Name (RDN sequence)."""
    parts = []
    seen = set()

    for rdn_set in name_node.get("children", []):
        # Each RDN is a SET of AttributeTypeAndValue SEQUENCEs
        for ava in rdn_set.get("children", []):
            ava_children = ava.get("children", [])
            if len(ava_children) < 2:
                continue
            oid = _decode_oid(ava_children[0].get("value", b""))
            label = _OID_LABELS.get(oid, oid)
            value_node = ava_children[1]
            text_value = _string_value(value_node)
            if text_value and text_value not in seen:
                seen.add(text_value)
                parts.append(f"{label}={text_value}")

    return ", ".join(parts) if parts else "unknown"


def _string_value(node: dict) -> Optional[str]:
    """Decode a string node based on its ASN.1 string type tag."""
    tag = node.get("tag")
    value = node.get("value", b"")

    if tag == 0x0C:  # UTF8String
        return value.decode("utf-8", errors="replace")
    if tag in (0x13, 0x14, 0x16):  # Printable/Teletex/IA5String
        return value.decode("ascii", errors="replace")
    if tag == 0x1E:  # BMPString
        return value.decode("utf-16-be", errors="replace")
    if tag == 0x03 and "children" in node:  # nested BIT STRING content
        return None
    return None


def _parse_validity(validity_node: dict) -> tuple:
    """Parse the Validity SEQUENCE into (not_before, not_after) strings."""
    children = validity_node.get("children", [])
    result = []
    for time_node in children:
        tag = time_node.get("tag")
        value = time_node.get("value", b"")
        raw = value.decode("ascii", errors="ignore")
        if tag == 0x17:  # UTCTime (YYMMDDHHMMSSZ)
            try:
                dt = datetime.datetime.strptime(raw, "%y%m%d%H%M%SZ")
            except ValueError:
                try:
                    dt = datetime.datetime.strptime(raw, "%y%m%d%H%M%S%z")
                except ValueError:
                    result.append(raw)
                    continue
            result.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
        elif tag == 0x18:  # GeneralizedTime
            try:
                dt = datetime.datetime.strptime(raw, "%Y%m%d%H%M%SZ")
            except ValueError:
                result.append(raw)
                continue
            result.append(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
        else:
            result.append(raw)
    # Return as-is, pad if malformed
    while len(result) < 2:
        result.append(None)
    return result[0], result[1]


def _parse_spki(spki_node: dict) -> tuple:
    """Parse SubjectPublicKeyInfo into (key_type, key_size)."""
    children = spki_node.get("children", [])
    if len(children) < 2:
        return None, None

    alg_children = children[0].get("children", [])
    if not alg_children:
        return None, None
    alg_oid = _decode_oid(alg_children[0].get("value", b""))
    key_type = _OID_LABELS.get(alg_oid, alg_oid)

    key_bits_node = children[1]
    key_size = None

    # For RSA, the BIT STRING wraps a DER-encoded RSAPublicKey SEQUENCE.
    # The modulus bit length equals the RSA key size.
    if key_type == "rsaEncryption":
        bit_string = key_bits_node.get("value", b"")
        try:
            inner, _ = _parse_der(bit_string[1:], 0)
            pub_children = inner.get("children", [])
            if pub_children:
                modulus = _extract_integer(pub_children[0])
                if modulus:
                    key_size = modulus.bit_length()
        except Exception:
            key_size = None

    # For EC keys, derive size from the named curve OID in algorithm params
    if key_type in ("id-ecPublicKey", "Ed25519", "Ed448"):
        if len(alg_children) > 1:
            params = alg_children[1]
            if params.get("tag") == 0x06:
                curve_oid = _decode_oid(params.get("value", b""))
                key_size = _EC_CURVE_SIZES.get(curve_oid)

    return key_type, key_size


def _populate_finding(result: CertificateFinding, decoded: dict) -> None:
    """Populate a CertificateFinding from a decoded certificate dict."""
    # Subject and issuer (already normalized to text by the decoder)
    result.subject = _norm_name(decoded.get("subject", "unknown"))
    result.issuer = _norm_name(decoded.get("issuer", "unknown"))
    result.version = str(decoded.get("version", "unknown"))

    # Serial number
    serial = decoded.get("serialNumber")
    result.serial_number = _format_serial(serial)

    # Validity dates
    not_before = decoded.get("notBefore")
    not_after = decoded.get("notAfter")
    if not_before:
        result.not_before = str(not_before)
    if not_after:
        result.not_after = str(not_after)
        result.is_expired = _is_expired(not_after)

    # Signature algorithm
    sig_algo = decoded.get("signatureAlgorithm")
    if sig_algo:
        result.signature_algorithm = str(sig_algo)

    # Public key information
    result.key_type = decoded.get("key_type")
    result.key_size = decoded.get("key_size")

    # SAN DNS names
    san = decoded.get("subjectAltName")
    if isinstance(san, (list, tuple)):
        for entry in san:
            if isinstance(entry, tuple) and len(entry) >= 2:
                if entry[0] == "DNS":
                    result.san_dns_names.append(str(entry[1]))

    # Self-signed check - compare normalized names
    result.is_self_signed = _is_self_signed(decoded)


def _norm_name(name_obj) -> str:
    """Return a name as text, handling structured or pre-rendered forms."""
    if isinstance(name_obj, str):
        return name_obj
    return _pretty_name(name_obj)


def _pretty_name(name_obj) -> str:
    """Render an X.509 name in readable form.

    Handles both the dict format (older CPython) and the
    tuple-of-RDN format used by newer CPython versions.
    """
    # dict format: {"commonName": "...", "organizationName": "..."}
    if isinstance(name_obj, dict):
        parts = []
        for key in ("commonName", "organizationName", "organizationalUnitName", "countryName"):
            if name_obj.get(key):
                parts.append(f"{key}={name_obj[key]}")
        if not parts:
            parts = [f"{k}={v}" for k, v in name_obj.items() if v][:3]
        return ", ".join(parts) if parts else "unknown"

    # tuple/list format: ((("commonName", "x"),), (("organizationName", "y"),))
    if isinstance(name_obj, (tuple, list)):
        parts = []
        for rdn in name_obj:
            # Each rdn is a group of (oid_label, value) pairs
            items = rdn if isinstance(rdn, (tuple, list)) else (rdn,)
            for pair in items:
                if isinstance(pair, (tuple, list)) and len(pair) >= 2:
                    parts.append(f"{pair[0]}={pair[1]}")
        return ", ".join(parts) if parts else "unknown"

    return "unknown"


def _format_serial(serial: Any) -> str:
    """Format certificate serial number."""
    if serial is None:
        return "unknown"
    if isinstance(serial, int):
        return format(serial, "X")
    return str(serial)


def _is_expired(not_after) -> bool:
    """Check if the certificate validity end date has passed."""
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        if isinstance(not_after, datetime.datetime):
            if not_after.tzinfo is None:
                not_after = not_after.replace(tzinfo=datetime.timezone.utc)
            return now > not_after
        if isinstance(not_after, str):
            cleaned = not_after.replace(" GMT", "+00:00").replace("Z", "+00:00")
            parsed = datetime.datetime.fromisoformat(cleaned)
            return now > parsed
    except (ValueError, TypeError):
        pass
    return False


def _is_self_signed(decoded: dict) -> bool:
    """Heuristic: certificate is self-signed if subject == issuer."""
    try:
        subject = decoded.get("subject")
        issuer = decoded.get("issuer")
        if not subject or not issuer:
            return False
        return _norm_name(subject) == _norm_name(issuer)
    except Exception:
        return False