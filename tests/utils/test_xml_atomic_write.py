"""Writing ModsConfig.xml must never leave a half-written file behind."""

from pathlib import Path

import pytest

from app.utils import json_utils
from app.utils.xml import json_to_xml_write, xml_path_to_json

MODS_CONFIG = {
    "ModsConfigData": {
        "version": "1.6.4633 rev1261",
        "activeMods": {"li": ["ludeon.rimworld", "brrainz.harmony"]},
    }
}


def test_writes_readable_mods_config(tmp_path: Path) -> None:
    target = tmp_path / "ModsConfig.xml"

    json_to_xml_write(MODS_CONFIG, str(target), raise_errs=True)

    parsed = xml_path_to_json(str(target))
    assert parsed["ModsConfigData"]["activeMods"]["li"] == [
        "ludeon.rimworld",
        "brrainz.harmony",
    ]


def test_failed_write_keeps_the_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "ModsConfig.xml"
    target.write_text("<ModsConfigData>previous</ModsConfigData>")

    def crash(source: str, destination: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(json_utils, "_replace_with_retry", crash)

    with pytest.raises(OSError, match="disk full"):
        json_to_xml_write(MODS_CONFIG, str(target), raise_errs=True)

    assert target.read_text() == "<ModsConfigData>previous</ModsConfigData>"
    assert [p.name for p in tmp_path.iterdir()] == ["ModsConfig.xml"]
