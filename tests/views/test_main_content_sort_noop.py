"""Sorting a list that is already in sorted order must not touch it."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.views import main_content_panel
from app.views.main_content_panel import MainContent

# Mod list UUIDs are the mods' paths as the OS spells them.
A, B, C = (str(Path("/m") / name) for name in ("a", "b", "c"))


def _content(order: list[str]) -> MagicMock:
    content = MagicMock()
    content.mods_panel.active_mods_list.paths = order
    content.metadata_controller.mods_metadata = {
        path: SimpleNamespace(mod_path=Path(path)) for path in (A, B, C)
    }
    return content


@pytest.fixture
def sorter_returns(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    results: list[list[str]] = []

    class FakeSorter:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.cycles: list[list[str]] = []
            self.tier_conflicts: list[tuple[str, str]] = []

        def sort(self) -> tuple[bool, list[str]]:
            return True, results[0]

    monkeypatch.setattr(main_content_panel, "Sorter", FakeSorter)
    return results


def test_unchanged_order_leaves_list_and_dividers_alone(
    sorter_returns: list[list[str]],
) -> None:
    content = _content([A, B])
    sorter_returns.append([A, B])

    MainContent._sort_active_mods(content, check_deps=False)

    content._insert_data_into_lists.assert_not_called()
    content.settings.save.assert_not_called()


def test_changed_order_is_applied(sorter_returns: list[list[str]]) -> None:
    content = _content([B, A])
    sorter_returns.append([A, B])

    MainContent._sort_active_mods(content, check_deps=False)

    active, inactive = content._insert_data_into_lists.call_args.args
    assert active == [A, B]
    assert inactive == [C]
