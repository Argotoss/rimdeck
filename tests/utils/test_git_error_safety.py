"""Git errors that look like corruption must never delete a mod's repository."""

from pathlib import Path
from unittest.mock import MagicMock

import pygit2
import pytest

from app.utils import git_utils
from app.utils.git_utils import (
    GitOperationConfig,
    GitOperationType,
    GitPullResult,
    _handle_git_error,
)
from app.utils.git_worker import process_batch_repository

CORRUPTION_ERROR = "object not found - no match for id (abc123)"


@pytest.fixture
def mod_repo(tmp_path: Path) -> pygit2.Repository:
    root = tmp_path / "SomeMod"
    pygit2.init_repository(str(root))
    repo = pygit2.Repository(str(root))
    (root / "About").mkdir()
    (root / "About" / "About.xml").write_text("<ModMetaData/>")
    repo.index.add_all()
    repo.index.write()
    sig = pygit2.Signature("t", "t@example.invalid")
    repo.create_commit("HEAD", sig, sig, "local work", repo.index.write_tree(), [])
    return repo


def _history(root: Path) -> int:
    repo = pygit2.Repository(str(root))
    return len(list(repo.walk(repo.head.target)))


def test_error_handler_keeps_the_repository(mod_repo: pygit2.Repository) -> None:
    root = Path(mod_repo.workdir)

    _handle_git_error(
        GitOperationType.PULL,
        Exception(CORRUPTION_ERROR),
        GitOperationConfig.create_silent(),
    )

    assert (root / ".git").is_dir()
    assert _history(root) == 1


def test_corruption_is_reported_with_a_hint_not_repaired(
    mod_repo: pygit2.Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = MagicMock()
    config = GitOperationConfig.create_silent()
    config.notify_errors = True
    monkeypatch.setattr(config, "get_handler", MagicMock(return_value=handler))

    _handle_git_error(GitOperationType.PULL, Exception(CORRUPTION_ERROR), config)

    message = handler.show_error.call_args.kwargs["message"]
    assert "Nothing was deleted" in message


def test_failed_fetch_is_an_error_not_up_to_date(
    mod_repo: pygit2.Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(mod_repo.workdir)
    mod_repo.remotes.create("origin", "https://example.invalid/mod.git")

    def broken_fetch(*args: object, **kwargs: object) -> None:
        raise pygit2.GitError(CORRUPTION_ERROR)

    monkeypatch.setattr(pygit2.remotes.Remote, "fetch", broken_fetch)

    result = git_utils.git_pull(mod_repo, config=GitOperationConfig.create_silent())

    assert result == GitPullResult.GIT_ERROR
    assert (root / ".git").is_dir()
    assert _history(root) == 1


def test_batch_worker_keeps_the_mod_folder(mod_repo: pygit2.Repository) -> None:
    root = Path(mod_repo.workdir)

    def failing_operation(repo: pygit2.Repository) -> None:
        raise pygit2.GitError(CORRUPTION_ERROR)

    ok, message = process_batch_repository(
        root, GitOperationConfig.create_silent(), failing_operation, "pull"
    )

    assert ok is False
    assert message is not None and "Nothing was deleted" in message
    assert (root / "About" / "About.xml").exists()
    assert _history(root) == 1
