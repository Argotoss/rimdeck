"""Write and sign the update manifest for a release.

Usage: python packaging/sign_update_manifest.py <artifacts_dir> <tag>

Reads the base64 Ed25519 private key from the ``UPDATE_SIGNING_KEY``
environment variable, hashes every file in ``artifacts_dir`` and writes
``manifest.json`` and ``manifest.json.sig`` next to them. The app verifies
both before installing an update.
"""

import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MANIFEST_NAME = "manifest.json"
SIGNATURE_NAME = "manifest.json.sig"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(artifacts_dir: Path, tag: str) -> bytes:
    """Return the canonical manifest bytes for every file in the directory."""
    assets = {
        path.name: file_sha256(path)
        for path in sorted(artifacts_dir.iterdir())
        if path.is_file() and path.name not in (MANIFEST_NAME, SIGNATURE_NAME)
    }
    if not assets:
        raise SystemExit(f"No release assets found in {artifacts_dir}")
    return json.dumps({"tag": tag, "assets": assets}, indent=2, sort_keys=True).encode(
        "utf-8"
    )


def sign(manifest: bytes, private_key_b64: str) -> bytes:
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
    return base64.b64encode(key.sign(manifest)) + b"\n"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    artifacts_dir, tag = Path(sys.argv[1]), sys.argv[2]
    private_key = os.environ.get("UPDATE_SIGNING_KEY", "").strip()
    if not private_key:
        raise SystemExit("UPDATE_SIGNING_KEY is not set; refusing to sign")
    manifest = build_manifest(artifacts_dir, tag)
    (artifacts_dir / MANIFEST_NAME).write_bytes(manifest)
    (artifacts_dir / SIGNATURE_NAME).write_bytes(sign(manifest, private_key))
    print(
        f"Signed manifest for {tag} covering {len(json.loads(manifest)['assets'])} assets"
    )


if __name__ == "__main__":
    main()
