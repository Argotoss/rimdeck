"""A theme that fails to load falls back to the default instead of crashing."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from app.controllers import theme_controller
from app.controllers.theme_controller import ThemeController


def test_missing_theme_warns_and_resets(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = ThemeController(default_theme="RimPy")
    monkeypatch.setattr(controller, "load_theme", lambda name: None)
    reset = MagicMock()
    monkeypatch.setattr(controller, "reset_to_default_theme", reset)
    warning = MagicMock()
    monkeypatch.setattr(theme_controller, "show_warning", warning)

    controller.apply_selected_theme(True, "Missing")

    reset.assert_called_once()
    text = warning.call_args.kwargs["text"]
    assert "Missing" in text
    assert "RimPy" in text
