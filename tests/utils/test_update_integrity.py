"""Tests for how the updater picks, verifies and stores a release."""

import hashlib
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from app.utils import update_utils
from app.utils.update_signing import ManifestError
from app.utils.update_utils import (
    UpdateDownloadError,
    UpdateManager,
    parse_version_string,
)
from packaging import version


class TestParseVersionString:
    def test_stable_tag(self) -> None:
        assert parse_version_string("v2.0.1") == version.parse("2.0.1")

    def test_edge_build_sorts_between_stable_releases(self) -> None:
        edge = parse_version_string("v2.0.1-edge4+abc1234")

        assert edge is not None
        assert version.parse("2.0.0") < edge < version.parse("2.0.1")

    def test_auto_build_is_comparable(self) -> None:
        assert parse_version_string("v1.4.0-auto12") == version.parse("1.4.0.dev12")

    @pytest.mark.parametrize("raw", ["Unknown version", "", "edge", "v2.0.1-edge"])
    def test_unrecognised_versions_return_none(self, raw: str) -> None:
        assert parse_version_string(raw) is None


class TestCurrentVersion:
    def _mgr(self) -> Any:
        mgr = MagicMock(spec=UpdateManager)
        mgr.tr = lambda text: text
        mgr._parse_current_version = UpdateManager._parse_current_version.__get__(mgr)
        return mgr

    def test_unknown_version_never_self_updates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        shown = MagicMock()
        monkeypatch.setattr(update_utils.dialogue, "show_information", shown)

        assert self._mgr()._parse_current_version("Unknown version") is None
        shown.assert_called_once()

    def test_release_version_parses_silently(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        shown = MagicMock()
        monkeypatch.setattr(update_utils.dialogue, "show_information", shown)

        assert self._mgr()._parse_current_version("v2.0.0") == version.parse("2.0.0")
        shown.assert_not_called()


class TestLinuxAssetChoice:
    def _mgr(self) -> Any:
        mgr = MagicMock(spec=UpdateManager)
        mgr._asset_matches = UpdateManager._asset_matches.__get__(mgr)
        mgr._find_best_asset_match = UpdateManager._find_best_asset_match.__get__(mgr)
        return mgr

    @pytest.mark.parametrize("reverse", [False, True])
    def test_two_ubuntu_builds_resolve_to_the_older_one(self, reverse: bool) -> None:
        assets = [
            {
                "name": "RimDeck-v2.0.1-Ubuntu-24.04_x86_64.tar.gz",
                "browser_download_url": "https://example.com/2404",
            },
            {
                "name": "RimDeck-v2.0.1-Ubuntu-22.04_x86_64.tar.gz",
                "browser_download_url": "https://example.com/2204",
            },
        ]
        if reverse:
            assets.reverse()

        match = self._mgr()._find_best_asset_match(
            assets, ["Linux", "Ubuntu"], ["x86_64"], ".tar.gz"
        )

        assert match is not None
        assert match["url"] == "https://example.com/2204"


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [
            self.content[i : i + chunk_size]
            for i in range(0, len(self.content), chunk_size)
        ]


def _download_mgr() -> Any:
    mgr = MagicMock(spec=UpdateManager)
    mgr._download_cancelled = False
    mgr._update_file = None
    mgr.update_progress = MagicMock()
    mgr._format_size = UpdateManager._format_size.__get__(mgr)
    mgr._get_file_size = MagicMock(return_value=0)
    mgr._create_temp_dir = UpdateManager._create_temp_dir.__get__(mgr)
    mgr._validate_download = UpdateManager._validate_download.__get__(mgr)
    mgr._download_with_progress = UpdateManager._download_with_progress.__get__(mgr)
    mgr._download_update = UpdateManager._download_update.__get__(mgr)
    return mgr


class TestVerifiedDownload:
    PAYLOAD = os.urandom(300_000)

    def test_matching_hash_is_streamed_to_disk(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            update_utils.http, "get", lambda *a, **k: _FakeResponse(self.PAYLOAD)
        )
        mgr = _download_mgr()

        mgr._download_update(
            "https://example.com/RimDeck.zip?x=1",
            hashlib.sha256(self.PAYLOAD).hexdigest(),
        )

        assert mgr._update_file.name == "RimDeck.zip"
        assert mgr._update_file.read_bytes() == self.PAYLOAD

    def test_hash_mismatch_is_refused_and_cleaned_up(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            update_utils.http, "get", lambda *a, **k: _FakeResponse(self.PAYLOAD)
        )
        created: list[Path] = []
        mgr = _download_mgr()
        real_create = mgr._create_temp_dir

        def track() -> Path:
            path = real_create()
            created.append(path)
            return path

        mgr._create_temp_dir = track

        with pytest.raises(UpdateDownloadError, match="signed release manifest"):
            mgr._download_update("https://example.com/RimDeck.zip", "0" * 64)

        assert mgr._update_file is None
        assert not created[0].exists()

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
    def test_staging_directory_is_private_and_unique(self) -> None:
        mgr = _download_mgr()
        first, second = mgr._create_temp_dir(), mgr._create_temp_dir()
        try:
            assert first != second
            assert (first.stat().st_mode & 0o777) == 0o700
        finally:
            first.rmdir()
            second.rmdir()


RELEASE_ASSETS: list[dict[str, Any]] = [
    {"name": "RimDeck-v2.0.1-Windows_x86_64.zip", "browser_download_url": "u1"},
    {"name": "manifest.json", "browser_download_url": "m"},
    {"name": "manifest.json.sig", "browser_download_url": "s"},
]


class TestManifestLookup:
    def _mgr(self) -> Any:
        mgr = MagicMock(spec=UpdateManager)
        mgr._verified_asset_hash = UpdateManager._verified_asset_hash.__get__(mgr)
        return mgr

    def test_returns_hash_for_selected_asset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            update_utils.http, "get", lambda url, **k: _FakeResponse(url.encode())
        )
        seen: list[tuple[bytes, bytes, str]] = []

        def fake_verify(manifest: bytes, signature: bytes, tag: str) -> dict[str, str]:
            seen.append((manifest, signature, tag))
            return {"RimDeck-v2.0.1-Windows_x86_64.zip": "a" * 64}

        monkeypatch.setattr(update_utils, "verify_manifest", fake_verify)

        digest = self._mgr()._verified_asset_hash(
            RELEASE_ASSETS, "v2.0.1", "RimDeck-v2.0.1-Windows_x86_64.zip", {}
        )

        assert digest == "a" * 64
        assert seen == [(b"m", b"s", "v2.0.1")]

    def test_release_without_manifest_is_refused(self) -> None:
        with pytest.raises(ManifestError, match="no signed update manifest"):
            self._mgr()._verified_asset_hash(RELEASE_ASSETS[:1], "v2.0.1", "x", {})

    def test_asset_missing_from_manifest_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            update_utils.http, "get", lambda url, **k: _FakeResponse(b"")
        )
        monkeypatch.setattr(update_utils, "verify_manifest", lambda *a: {})

        with pytest.raises(ManifestError, match="does not list"):
            self._mgr()._verified_asset_hash(
                RELEASE_ASSETS, "v2.0.1", "RimDeck-v2.0.1-Windows_x86_64.zip", {}
            )

    def test_unreachable_manifest_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*a: Any, **k: Any) -> None:
            raise requests.ConnectionError("offline")

        monkeypatch.setattr(update_utils.http, "get", boom)

        with pytest.raises(ManifestError, match="Could not download"):
            self._mgr()._verified_asset_hash(RELEASE_ASSETS, "v2.0.1", "x", {})
