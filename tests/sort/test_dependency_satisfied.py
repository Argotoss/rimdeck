"""The one rule every dependency check uses."""

from app.sort.dependencies import dependency_satisfied


def test_present_dependency() -> None:
    assert dependency_satisfied("a.lib", [], {"a.lib"}, use_alternatives=False)


def test_alternative_counts_only_when_enabled() -> None:
    assert dependency_satisfied("a.lib", ["b.lib"], {"b.lib"}, use_alternatives=True)
    assert not dependency_satisfied(
        "a.lib", ["b.lib"], {"b.lib"}, use_alternatives=False
    )


def test_known_replacement_counts() -> None:
    assert dependency_satisfied(
        "brrainz.harmony", [], {"zetrith.prepatcher"}, use_alternatives=False
    )


def test_missing_dependency() -> None:
    assert not dependency_satisfied("a.lib", ["b.lib"], set(), use_alternatives=True)
