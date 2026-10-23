"""Tests for signed update manifests and the release signing script."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.utils.update_signing import (
    UPDATE_PUBLIC_KEY,
    ManifestError,
    sha256_file,
    verify_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_signer() -> ModuleType:
    # The repo's packaging/ folder shadows nothing at import time but shares
    # its name with the PyPI package, so load the script by path.
    spec = importlib.util.spec_from_file_location(
        "sign_update_manifest", REPO_ROOT / "packaging" / "sign_update_manifest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def keypair() -> tuple[str, str]:
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(private).decode(), base64.b64encode(public).decode()


@pytest.fixture
def signed_release(tmp_path: Path, keypair: tuple[str, str]) -> tuple[Path, str]:
    signer = _load_signer()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "RimDeck-v2.0.1-Darwin_arm64.tar.gz").write_bytes(b"mac build")
    (artifacts / "RimDeck-v2.0.1-Windows_x86_64.zip").write_bytes(b"win build")
    manifest = signer.build_manifest(artifacts, "v2.0.1")
    (artifacts / "manifest.json").write_bytes(manifest)
    (artifacts / "manifest.json.sig").write_bytes(signer.sign(manifest, keypair[0]))
    return artifacts, keypair[1]


def _read(artifacts: Path) -> tuple[bytes, bytes]:
    return (
        (artifacts / "manifest.json").read_bytes(),
        (artifacts / "manifest.json.sig").read_bytes(),
    )


def test_signed_manifest_verifies_and_lists_every_asset(
    signed_release: tuple[Path, str],
) -> None:
    artifacts, public = signed_release
    manifest, signature = _read(artifacts)

    hashes = verify_manifest(manifest, signature, "v2.0.1", public_key=public)

    assert hashes == {
        "RimDeck-v2.0.1-Darwin_arm64.tar.gz": hashlib.sha256(b"mac build").hexdigest(),
        "RimDeck-v2.0.1-Windows_x86_64.zip": hashlib.sha256(b"win build").hexdigest(),
    }


def test_tampered_manifest_is_rejected(signed_release: tuple[Path, str]) -> None:
    artifacts, public = signed_release
    manifest, signature = _read(artifacts)
    data = json.loads(manifest)
    data["assets"]["RimDeck-v2.0.1-Windows_x86_64.zip"] = "0" * 64
    tampered = json.dumps(data, indent=2, sort_keys=True).encode()

    with pytest.raises(ManifestError, match="signature"):
        verify_manifest(tampered, signature, "v2.0.1", public_key=public)


def test_manifest_signed_by_another_key_is_rejected(
    signed_release: tuple[Path, str],
) -> None:
    artifacts, _ = signed_release
    manifest, signature = _read(artifacts)

    with pytest.raises(ManifestError, match="signature"):
        verify_manifest(manifest, signature, "v2.0.1", public_key=UPDATE_PUBLIC_KEY)


def test_manifest_for_another_release_is_rejected(
    signed_release: tuple[Path, str],
) -> None:
    artifacts, public = signed_release
    manifest, signature = _read(artifacts)

    with pytest.raises(ManifestError, match="expected 'v2.0.2'"):
        verify_manifest(manifest, signature, "v2.0.2", public_key=public)


def test_garbage_signature_is_rejected(signed_release: tuple[Path, str]) -> None:
    artifacts, public = signed_release
    manifest, _ = _read(artifacts)

    with pytest.raises(ManifestError, match="signature"):
        verify_manifest(manifest, b"not base64!", "v2.0.1", public_key=public)


def test_signer_refuses_to_run_without_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    signer = _load_signer()
    (tmp_path / "asset.zip").write_bytes(b"x")
    monkeypatch.delenv("UPDATE_SIGNING_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["sign", str(tmp_path), "v2.0.1"])

    with pytest.raises(SystemExit, match="UPDATE_SIGNING_KEY"):
        signer.main()
    assert not (tmp_path / "manifest.json").exists()


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    data = b"a" * (3 * 1024 * 1024 + 7)
    path = tmp_path / "big.bin"
    path.write_bytes(data)

    assert sha256_file(path) == hashlib.sha256(data).hexdigest()
