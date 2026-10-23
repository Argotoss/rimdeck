"""Settings saved with the removed alphabetical sort load as topological."""

from app.models.settings import Settings
from app.utils.constants import SortMethod


def test_alphabetical_setting_becomes_topological() -> None:
    settings = Settings()

    settings._from_dict({"sorting_algorithm": "Alphabetical"})

    assert settings.sorting_algorithm == SortMethod.TOPOLOGICAL


def test_topological_setting_is_kept() -> None:
    settings = Settings()

    settings._from_dict({"sorting_algorithm": "Topological"})

    assert settings.sorting_algorithm == SortMethod.TOPOLOGICAL
