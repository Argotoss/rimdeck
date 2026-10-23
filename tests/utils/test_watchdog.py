"""Tests for WatchdogHandler lifecycle methods."""

from __future__ import annotations

from threading import Timer
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject


def _make_handler(acf_alive: bool = True, mods_alive: bool = True) -> Any:
    """Create a WatchdogHandler without real observers."""
    from app.utils.watchdog import WatchdogHandler

    handler = WatchdogHandler.__new__(WatchdogHandler)
    QObject.__init__(handler)

    handler.watchdog_acf_observer = MagicMock()
    handler.watchdog_acf_observer.is_alive.return_value = acf_alive
    handler.watchdog_mods_observer = MagicMock()
    handler.watchdog_mods_observer.is_alive.return_value = mods_alive
    handler.cooldown_timers = {
        "t1": MagicMock(spec=Timer),
        "t2": MagicMock(spec=Timer),
    }
    return handler


class TestWatchdogHandlerStop:
    """Tests for WatchdogHandler.stop() method."""

    def test_stop_both_observers_alive(self, qapp: object) -> None:
        """Both observers alive: both must be stopped and joined."""
        handler = _make_handler(acf_alive=True, mods_alive=True)
        acf_obs = handler.watchdog_acf_observer
        mods_obs = handler.watchdog_mods_observer

        handler.stop()

        acf_obs.stop.assert_called_once()
        acf_obs.join.assert_called_once()
        mods_obs.stop.assert_called_once()
        mods_obs.join.assert_called_once()

    def test_stop_only_acf_alive(self, qapp: object) -> None:
        """Only ACF alive: ACF stopped, mods skipped."""
        handler = _make_handler(acf_alive=True, mods_alive=False)
        acf_obs = handler.watchdog_acf_observer
        mods_obs = handler.watchdog_mods_observer

        handler.stop()

        acf_obs.stop.assert_called_once()
        mods_obs.stop.assert_not_called()

    def test_stop_only_mods_alive(self, qapp: object) -> None:
        """Only mods alive: mods stopped, ACF skipped."""
        handler = _make_handler(acf_alive=False, mods_alive=True)
        acf_obs = handler.watchdog_acf_observer
        mods_obs = handler.watchdog_mods_observer

        handler.stop()

        acf_obs.stop.assert_not_called()
        mods_obs.stop.assert_called_once()

    @pytest.mark.parametrize(
        "acf_alive,mods_alive",
        [(True, True), (True, False), (False, True), (False, False)],
    )
    def test_stop_always_cancels_timers(
        self, qapp: object, acf_alive: bool, mods_alive: bool
    ) -> None:
        """Timers must always be cancelled regardless of which observers were alive."""
        handler = _make_handler(acf_alive=acf_alive, mods_alive=mods_alive)
        timers = list(handler.cooldown_timers.values())

        handler.stop()

        for timer in timers:
            timer.cancel.assert_called_once()

    def test_stop_clears_timers_dict(self, qapp: object) -> None:
        """Timers dict must be empty after stop."""
        handler = _make_handler()

        handler.stop()

        assert handler.cooldown_timers == {}

    def test_stop_nulls_observers(self, qapp: object) -> None:
        """Observers must be None after stop."""
        handler = _make_handler()

        handler.stop()

        assert handler.watchdog_acf_observer is None
        assert handler.watchdog_mods_observer is None

    def test_stop_none_observers_is_noop(self, qapp: object) -> None:
        """Calling stop when observers are already None should not raise."""
        handler = _make_handler()
        handler.watchdog_acf_observer = None
        handler.watchdog_mods_observer = None
        handler.cooldown_timers = {}

        handler.stop()  # should not raise

    def test_stop_idempotent(self, qapp: object) -> None:
        """Calling stop twice should not raise."""
        handler = _make_handler()

        handler.stop()
        handler.stop()  # second call is a noop


class TestWatchdogHandlerStart:
    """Tests for WatchdogHandler.start() method."""

    def test_start_both_observers(self, qapp: object) -> None:
        """Both observers present: both must be started."""
        handler = _make_handler(acf_alive=False, mods_alive=False)

        handler.start()

        handler.watchdog_acf_observer.start.assert_called_once()
        handler.watchdog_mods_observer.start.assert_called_once()

    def test_start_skips_already_alive_with_warning(self, qapp: object) -> None:
        """If an observer is already alive, skip it and log a warning."""
        handler = _make_handler(acf_alive=True, mods_alive=True)

        handler.start()  # should not raise

        handler.watchdog_acf_observer.start.assert_not_called()
        handler.watchdog_mods_observer.start.assert_not_called()

    def test_start_none_observers_logs_warning(self, qapp: object) -> None:
        """None observers should log warnings, not crash."""
        handler = _make_handler()
        handler.watchdog_acf_observer = None
        handler.watchdog_mods_observer = None

        handler.start()  # should not raise


def _make_move_handler(known: set[str], about_to_mod: dict[str, str]) -> Any:
    """Handler with a fake metadata controller and a recording cooldown."""
    from app.utils.watchdog import WatchdogHandler

    handler: Any = WatchdogHandler.__new__(WatchdogHandler)
    QObject.__init__(handler)
    handler.workshop_acf_path = None
    handler.steamcmd_appworkshop_acf_path = "/nonexistent/appworkshop_294100.acf"
    handler._instance = MagicMock()
    handler.metadata_controller = MagicMock()
    handler.metadata_controller.mods_metadata = dict.fromkeys(known)
    handler.metadata_controller.resolve_about_xml_to_mod_path.side_effect = (
        about_to_mod.get
    )
    handler.calls = []
    handler._WatchdogHandler__cooldown_mod_change = lambda callback: (
        handler.calls.append(callback)
    )
    return handler


def _moved(src: str, dest: str, is_directory: bool) -> Any:
    from watchdog.events import DirMovedEvent, FileMovedEvent

    if is_directory:
        return DirMovedEvent(src, dest)
    return FileMovedEvent(src, dest)


class TestWatchdogHandlerMoves:
    def test_renamed_mod_folder_is_removed_and_added(
        self, qapp: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.utils.watchdog.resolve_data_source", lambda instance, path: "local"
        )
        handler = _make_move_handler({"/Mods/Old"}, {})

        handler.on_moved(_moved("/Mods/Old", "/Mods/New", is_directory=True))

        assert handler.calls == [
            {"operation": "deleted", "path": "/Mods/Old"},
            {"operation": "created", "data_source": "local", "path": "/Mods/New"},
        ]

    def test_mod_folder_moved_outside_mod_sources_is_only_removed(
        self, qapp: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.utils.watchdog.resolve_data_source", lambda instance, path: None
        )
        handler = _make_move_handler({"/Mods/Old"}, {})

        handler.on_moved(_moved("/Mods/Old", "/Trash/Old", is_directory=True))

        assert handler.calls == [{"operation": "deleted", "path": "/Mods/Old"}]

    def test_about_xml_saved_by_rename_updates_the_mod(self, qapp: object) -> None:
        about = "/Mods/A/About/About.xml"
        handler = _make_move_handler({"/Mods/A"}, {about: "/Mods/A"})

        handler.on_moved(
            _moved("/Mods/A/About/About.xml.tmp", about, is_directory=False)
        )

        assert handler.calls == [{"operation": "updated", "path": "/Mods/A"}]

    def test_unrelated_file_move_is_ignored(self, qapp: object) -> None:
        handler = _make_move_handler({"/Mods/A"}, {})

        handler.on_moved(_moved("/Mods/A/a.txt", "/Mods/A/b.txt", is_directory=False))

        assert handler.calls == []
