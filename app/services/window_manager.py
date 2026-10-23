"""Service for tracking and managing MainContent child windows."""

from typing import Any

from PySide6.QtWidgets import QWidget


class WindowManager:
    """Tracks child windows owned by MainContent and provides cleanup.

    Handles both instance-attribute windows (e.g. ``self.rule_editor``)
    and list-tracked windows (created as local variables).
    """

    def __init__(self) -> None:
        self._child_windows: list[QWidget] = []
        self._tracked_attrs: list[tuple[Any, str]] = []

    def register(self, window: QWidget) -> None:
        """Track a window that was created as a local variable."""
        self._child_windows.append(window)

    def register_attr(self, instance: Any, attr_name: str) -> None:
        """Track an instance attribute that holds a window reference."""
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
