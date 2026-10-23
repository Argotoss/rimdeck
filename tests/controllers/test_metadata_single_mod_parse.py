"""Reloading one mod parses it with the same settings as a full refresh."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.controllers import metadata_controller
from app.controllers.metadata_controller import MetadataController


def test_single_mod_uses_content_root_and_lookup_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod_folder = tmp_path / "Mods" / "SomeMod"
    mod_folder.mkdir(parents=True)
    content_root = tmp_path / "RimWorld.app" / "Contents" / "Resources"
    monkeypatch.setattr(
        metadata_controller,
        "resolve_game_layout",
        lambda game_path: SimpleNamespace(content_root=content_root),
    )
    controller = MagicMock()
    controller.settings.prefer_versioned_about_tags = True
    controller.settings.case_insensitive_about_xml_lookup = False
    controller.mods_metadata = {}

    MetadataController._parse_single_mod(controller, str(mod_folder))

    args = controller.metadata_mediator.create_parser_worker.call_args.args
    assert args[0] == [mod_folder]
    assert args[1] == content_root
    assert args[3:] == (True, False)
