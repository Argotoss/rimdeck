"""Rule loops found by Sort are explained with mod names and rule sources."""

from unittest.mock import MagicMock

import pytest

from app.views import main_content_panel
from app.views.main_content_panel import MainContent


def test_loop_report_names_mods_and_rule_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = MagicMock()
    content.tr = lambda text: text
    content.metadata_controller.get_mod_name_from_package_id = {
        "mod.a": "Alpha",
        "mod.b": "Beta",
    }.get
    sorter = MagicMock()
    sorter.cycles = [["mod.a", "mod.b"]]
    sorter.cycle_edge_sources = lambda later, earlier: (
        ["user"] if later == "mod.a" else ["about", "community"]
    )
    warning = MagicMock()
    monkeypatch.setattr(main_content_panel.dialogue, "show_warning", warning)

    MainContent._report_rule_cycles(content, sorter)

    details = warning.call_args.kwargs["details"]
    assert details == (
        "Alpha loads after Beta (your rules)\n"
        "Beta loads after Alpha (its About.xml, community rules)"
    )


def test_tier_conflict_report_names_both_mods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = MagicMock()
    content.tr = lambda text: text
    content.metadata_controller.get_mod_name_from_package_id = {
        "mod.z": "Z Last",
        "mod.h": "HugsLib",
    }.get
    sorter = MagicMock()
    sorter.tier_conflicts = [("mod.z", "mod.h")]
    warning = MagicMock()
    monkeypatch.setattr(main_content_panel.dialogue, "show_warning", warning)

    MainContent._report_tier_conflicts(content, sorter)

    assert warning.call_args.kwargs["details"] == (
        "Z Last is marked to load last, but HugsLib, which loads near the top,"
        " has to load after it."
    )
