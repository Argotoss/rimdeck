"""Closed windows must not pile up or keep repopulating on every refresh."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from app.services.window_manager import WindowManager


def _shown(qtbot: QtBot) -> QWidget:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_closed_windows_are_dropped_on_next_register(qtbot: QtBot) -> None:
    manager = WindowManager()
    first = _shown(qtbot)
    manager.register(first)
    first.close()

    second = _shown(qtbot)
    manager.register(second)

    assert manager._child_windows == [second]


def test_keyed_window_replaces_the_previous_one(qtbot: QtBot) -> None:
    manager = WindowManager()
    first = _shown(qtbot)
    manager.register(first, key="duplicate_mods")

    second = _shown(qtbot)
    manager.register(second, key="duplicate_mods")

    assert not first.isVisible()
    assert second.isVisible()


def test_attributes_are_tracked_once() -> None:
    manager = WindowManager()
    owner = object()

    manager.register_attr(owner, "rule_editor")
    manager.register_attr(owner, "rule_editor")

    assert manager._tracked_attrs == [(owner, "rule_editor")]


def test_hidden_panel_repopulates_only_when_shown(
    qtbot: QtBot,
    mock_metadata_controller: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.windows.duplicate_mods_panel import DuplicateModsPanel

    mock_metadata_controller.settings = MagicMock()
    panel = DuplicateModsPanel({}, metadata_controller=mock_metadata_controller)
    qtbot.addWidget(panel)
    panel.close()
    populate = MagicMock()
    monkeypatch.setattr(panel, "_populate_from_metadata", populate)

    panel._on_metadata_refreshed()
    panel._on_metadata_refreshed()
    assert populate.call_count == 0

    panel.show()
    assert populate.call_count == 1

    panel._on_metadata_refreshed()
    assert populate.call_count == 2
