"""A malformed About.xml makes the mod invalid, as it does in RimWorld."""

from pathlib import Path

from app.models.metadata.metadata_factory import _create_about_mod_from_xml
from app.utils.xml import xml_path_to_json

BROKEN = "<ModMetaData><name>Broken</name><packageId>a.broken</packageId>"
VALID = (
    "<ModMetaData><name>Fine</name><packageId>a.fine</packageId>"
    "<supportedVersions><li>1.6</li></supportedVersions></ModMetaData>"
)


def _write(tmp_path: Path, folder: str, content: str) -> tuple[Path, Path]:
    about = tmp_path / folder / "About" / "About.xml"
    about.parent.mkdir(parents=True)
    about.write_text(content)
    return tmp_path / folder, about


def test_malformed_about_xml_is_invalid_but_listed(tmp_path: Path) -> None:
    base, about = _write(tmp_path, "BrokenMod", BROKEN)

    valid, mod = _create_about_mod_from_xml(base, about, "1.6")

    assert valid is False
    assert mod.valid is False
    assert mod.mod_path == base
    assert mod.name == "BrokenMod"


def test_well_formed_about_xml_still_parses(tmp_path: Path) -> None:
    base, about = _write(tmp_path, "FineMod", VALID)

    valid, mod = _create_about_mod_from_xml(base, about, "1.6")

    assert valid is True
    assert str(mod.package_id) == "a.fine"


def test_other_files_keep_the_lenient_fallback(tmp_path: Path) -> None:
    _, about = _write(tmp_path, "Other", BROKEN)

    assert xml_path_to_json(str(about), strict=True) == {}
    assert xml_path_to_json(str(about)) != {}
