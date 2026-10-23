"""A sort started while another is waiting on its dialog is ignored."""

from unittest.mock import MagicMock

from app.views.main_content_panel import MainContent


def test_reentrant_sort_is_ignored() -> None:
    content = MagicMock()
    content._sort_in_progress = False
    calls: list[bool] = []

    def sort_that_reenters(check_deps: bool) -> None:
        calls.append(check_deps)
        MainContent._do_sort(content, check_deps=False)

    content._sort_active_mods.side_effect = sort_that_reenters

    MainContent._do_sort(content, check_deps=True)

    assert calls == [True]
    assert content._sort_in_progress is False


def test_failed_sort_releases_the_guard() -> None:
    content = MagicMock()
    content._sort_in_progress = False
    content._sort_active_mods.side_effect = RuntimeError("boom")

    try:
        MainContent._do_sort(content)
    except RuntimeError:
        pass

    assert content._sort_in_progress is False
