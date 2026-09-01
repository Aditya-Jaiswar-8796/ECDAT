"""Dependency schema.

Describes a third-party library dependency detected in the scanned project
by Member 4. Used to flag outdated or crypto-relevant (EOL) dependencies and
to enrich the final risk assessment.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Dependency(BaseModel):
    """A single detected dependency and its relevant metadata."""

    # Name + version is the natural identity for a dependency.
    name: str
    version: Optional[str] = None

    # Optional ecosystem / manager hint, e.g. "maven", "npm", "pip".
    ecosystem: Optional[str] = None

    # Crypto-relevant flag: whether this dependency is a security/crypto lib
    # (e.g. bouncycastle, openssl) worth extra scrutiny.
    crypto_relevant: bool = False

    # Vendor-reported patch/security note if any.
    known_vulnerabilities: Optional[str] = None
    latest_version: Optional[str] = None

    model_config = {"from_attributes": True}
