"""Service for tracking and managing MainContent child windows."""

from typing import Any

from PySide6.QtWidgets import QWidget
from shiboken6 import isValid


class WindowManager:
    """Tracks child windows owned by MainContent and provides cleanup.

    Handles both instance-attribute windows (e.g. ``self.rule_editor``)
    and list-tracked windows (created as local variables).
    """

    def __init__(self) -> None:
        self._child_windows: list[QWidget] = []
        self._tracked_attrs: list[tuple[Any, str]] = []
        self._keyed_windows: dict[str, QWidget] = {}

    def register(self, window: QWidget, key: str | None = None) -> None:
        """Track a window that was created as a local variable.

        Windows that have been closed since they were registered are dropped
        first, so nothing keeps them alive. With a ``key``, the previous
        window registered under that key is closed, so prompts that reopen on
        every refresh replace each other instead of stacking up.

        :param window: The window to track.
        :param key: Optional identity for windows that should exist only once.
        """
        self._child_windows = [w for w in self._child_windows if _is_open(w)]
        if key is not None:
            previous = self._keyed_windows.pop(key, None)
            if previous is not None and previous is not window and isValid(previous):
                previous.close()
            self._keyed_windows[key] = window
        self._child_windows.append(window)

    def register_attr(self, instance: Any, attr_name: str) -> None:
        """Track an instance attribute that holds a window reference."""
        if (instance, attr_name) not in self._tracked_attrs:
            self._tracked_attrs.append((instance, attr_name))

    def close_all(self) -> None:
        """Close all tracked windows and clear tracking lists."""
        for instance, attr_name in self._tracked_attrs:
            window = getattr(instance, attr_name, None)
            if window is not None:
                try:
                    window.close()
                except Exception:  # noqa: S110
                    # Avoid RuntimeError: libshiboken: Internal C++ object (Panel) already deleted.
                    pass
        for window in self._child_windows:
            if window is not None:
                try:
                    window.close()
                except Exception:  # noqa: S110
                    # Avoid RuntimeError: libshiboken: Internal C++ object (Panel) already deleted.
                    pass
        self._child_windows.clear()
        self._tracked_attrs.clear()
        self._keyed_windows.clear()


def _is_open(window: QWidget) -> bool:
    return isValid(window) and window.isVisible()
