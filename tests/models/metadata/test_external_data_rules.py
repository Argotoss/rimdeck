"""Community incompatibilities and Steam required items reach the mod's rules."""

from pathlib import Path

import msgspec

from app.models.metadata.metadata_factory import (
    create_rules_from_external_rules,
    steam_required_dependencies,
)
from app.models.metadata.metadata_structure import (
    AboutXmlMod,
    CaseInsensitiveStr,
    DependencyMod,
    ExternalRulesSchema,
    ModType,
    SteamDbEntry,
    SteamDbSchema,
)

COMMUNITY_JSON = b"""{
  "timestamp": 1,
  "rules": {
    "shilica.smallerplanet": {
      "incompatibleWith": {
        "oblitus.mylittleplanet": {"name": "My Little Planet", "comment": "Overlap"}
      }
    }
  }
}"""


def test_community_incompatibilities_are_kept() -> None:
    schema = msgspec.json.decode(COMMUNITY_JSON, type=ExternalRulesSchema)

    rules = create_rules_from_external_rules(schema.rules["shilica.smallerplanet"])

    assert "oblitus.mylittleplanet" in rules.incompatible_with


def _workshop_mod(
    tmp_path: Path, workshop_id: str, mod_type: ModType = ModType.STEAM_WORKSHOP
) -> AboutXmlMod:
    folder = tmp_path / workshop_id
    folder.mkdir()
    mod = AboutXmlMod(name="Uses Library", package_id=CaseInsensitiveStr("a.user"))
    mod.mod_type = mod_type
    mod._mod_path = folder
    return mod


STEAM_DB = SteamDbSchema(
    database={
        "100": SteamDbEntry(packageId="a.user", dependencies={"200": ["Lib", "u"]}),
        "200": SteamDbEntry(packageId="b.library", name="Library", url="lib-url"),
    }
)


def test_workshop_mod_without_declared_dependencies_uses_steam(tmp_path: Path) -> None:
    deps = steam_required_dependencies(_workshop_mod(tmp_path, "100"), STEAM_DB)

    assert list(deps) == ["b.library"]
    assert deps[CaseInsensitiveStr("b.library")].name == "Library"


def test_declared_dependencies_are_trusted(tmp_path: Path) -> None:
    mod = _workshop_mod(tmp_path, "100")
    mod.about_rules.dependencies = {
        CaseInsensitiveStr("c.other"): DependencyMod(
            package_id=CaseInsensitiveStr("c.other")
        )
    }

    assert steam_required_dependencies(mod, STEAM_DB) == {}


def test_local_mods_ignore_steam_data(tmp_path: Path) -> None:
    mod = _workshop_mod(tmp_path, "100", mod_type=ModType.LOCAL)

    assert steam_required_dependencies(mod, STEAM_DB) == {}
