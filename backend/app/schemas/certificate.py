"""Certificate schema.

Describes a cryptographic certificate (or key store/cert chain) discovered in
the scanned project by Member 4. Used to flag expired, self-signed or weak
certificates in the risk assessment.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Certificate(BaseModel):
    """A single certificate discovered in the scanned source bundle."""

    subject: Optional[str] = None
    issuer: Optional[str] = None

    # Serial / fingerprint for stable identification of the cert.
    serial_number: Optional[str] = None
    fingerprint_sha256: Optional[str] = None

    not_valid_before: Optional[str] = None
    not_valid_after: Optional[str] = None
    signature_algorithm: Optional[str] = None
    key_algorithm: Optional[str] = None
    key_size: Optional[int] = None

    # Where the certificate was found in the bundle (e.g. keystore file).
    source_file: Optional[str] = None

    model_config = {"from_attributes": True}
