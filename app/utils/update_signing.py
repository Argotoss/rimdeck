"""Signed update manifests.

Every release publishes ``manifest.json`` (release tag plus the SHA-256 of each
asset) and ``manifest.json.sig`` (a base64 Ed25519 signature over the manifest
bytes). The updater only installs an asset whose hash is listed in a manifest
that verifies against :data:`UPDATE_PUBLIC_KEY`.
"""

import base64
import binascii
import hashlib
import json
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MANIFEST_ASSET_NAME = "manifest.json"
SIGNATURE_ASSET_NAME = "manifest.json.sig"
UPDATE_PUBLIC_KEY = "af7KKIOh1j4GsPUMQtFT3k0KhSGnE5Z6Zf1krkg/9V8="

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_HASH_CHUNK_SIZE = 1024 * 1024


class ManifestError(Exception):
    """The release manifest is missing, malformed or not signed by our key."""


def verify_manifest(
    manifest: bytes,
    signature: bytes,
    expected_tag: str,
    public_key: str = UPDATE_PUBLIC_KEY,
) -> dict[str, str]:
    """Verify a signed manifest and return its asset hashes.

    :param manifest: Raw bytes of ``manifest.json`` as published.
    :param signature: Raw bytes of ``manifest.json.sig`` (base64 text).
    :param expected_tag: Tag of the release the manifest was downloaded from.
    :param public_key: Base64 Ed25519 public key to verify against.
    :return: Mapping of asset file name to lowercase hex SHA-256.
    :raises ManifestError: If the signature, tag or structure is invalid.
    """
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key))
        key.verify(base64.b64decode(signature.strip(), validate=True), manifest)
    except (InvalidSignature, ValueError, binascii.Error) as e:
        raise ManifestError("Update manifest signature is invalid") from e

    try:
        data = json.loads(manifest)
    except ValueError as e:
        raise ManifestError("Update manifest is not valid JSON") from e
    if not isinstance(data, dict):
        raise ManifestError("Update manifest has an unexpected structure")

    if data.get("tag") != expected_tag:
        raise ManifestError(
            f"Update manifest is for {data.get('tag')!r}, expected {expected_tag!r}"
        )

    assets = data.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise ManifestError("Update manifest lists no assets")
    hashes: dict[str, str] = {}
    for name, digest in assets.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ManifestError("Update manifest has an unexpected structure")
        if not _SHA256_PATTERN.match(digest):
            raise ManifestError(f"Update manifest has an invalid hash for {name}")
        hashes[name] = digest
    return hashes


def sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
