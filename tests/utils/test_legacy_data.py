"""Tests for the one-time import of the original app's data."""

import json
from pathlib import Path

from app.utils.legacy_data import import_legacy_data


def _legacy_folder(root: Path) -> Path:
    legacy = root / "OldApp"
    (legacy / "instances" / "Default").mkdir(parents=True)
    (legacy / "modlists").mkdir()
    (legacy / "modlists" / "favourite.xml").write_text("<list/>")
    (legacy / "old.lock").write_text("123")
    settings = {
        "theme_name": "RimPy",
        "current_instance_path": str(legacy / "instances" / "Default"),
        "instances": {
            "Default": {
                "steamcmd_install_path": str(legacy / "instances" / "Default"),
                "game_folder": "/games/RimWorld",
            }
        },
    }
    (legacy / "settings.json").write_text(json.dumps(settings))
    return legacy


def test_imports_data_and_rewrites_paths(tmp_path: Path) -> None:
    legacy = _legacy_folder(tmp_path)
    new = tmp_path / "RimDeck"

    assert import_legacy_data(new, legacy) is True

    settings = json.loads((new / "settings.json").read_text())
    assert settings["current_instance_path"] == str(new / "instances" / "Default")
    default = settings["instances"]["Default"]
    assert default["steamcmd_install_path"] == str(new / "instances" / "Default")
    assert default["game_folder"] == "/games/RimWorld"
    assert (new / "modlists" / "favourite.xml").read_text() == "<list/>"
    assert not (new / "old.lock").exists()


def test_original_folder_is_left_untouched(tmp_path: Path) -> None:
    legacy = _legacy_folder(tmp_path)
    before = (legacy / "settings.json").read_text()

    import_legacy_data(tmp_path / "RimDeck", legacy)

    assert (legacy / "settings.json").read_text() == before
    assert (legacy / "old.lock").exists()


def test_existing_settings_are_never_overwritten(tmp_path: Path) -> None:
    legacy = _legacy_folder(tmp_path)
    new = tmp_path / "RimDeck"
    new.mkdir()
    (new / "settings.json").write_text('{"theme_name": "Modern"}')

    assert import_legacy_data(new, legacy) is False
    assert json.loads((new / "settings.json").read_text()) == {"theme_name": "Modern"}


def test_nothing_happens_without_original_data(tmp_path: Path) -> None:
    new = tmp_path / "RimDeck"

    assert import_legacy_data(new, tmp_path / "missing") is False
    assert not new.exists()


def test_unreadable_original_settings_leave_a_clean_first_run(tmp_path: Path) -> None:
    legacy = _legacy_folder(tmp_path)
    (legacy / "settings.json").write_text("{not json")
    new = tmp_path / "RimDeck"

    assert import_legacy_data(new, legacy) is False
    assert not (new / "settings.json").exists()
