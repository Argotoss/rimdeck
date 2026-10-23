"""Show what _handle_git_error's 'corruption repair' does to a healthy mod repo."""
import shutil
from pathlib import Path

import pygit2
from loguru import logger

logger.remove()
from app.utils.git_utils import GitOperationConfig, GitOperationType, _handle_git_error

root = Path("dev/tmp_git_mod").resolve()
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
repo = pygit2.init_repository(str(root))
(root / "About").mkdir()
(root / "About" / "About.xml").write_text("<ModMetaData/>")
repo.index.add_all(); repo.index.write()
sig = pygit2.Signature("t", "t@example.invalid")
repo.create_commit("HEAD", sig, sig, "local work", repo.index.write_tree(), [])
print("before: .git exists =", (root / ".git").exists(), "commits =", len(list(repo.walk(repo.head.target))))
err = Exception("object not found - no match for id (abc123)")
repaired = _handle_git_error(
    GitOperationType.PULL, err, GitOperationConfig.create_silent(),
    repo_path=repo.path, repo_url=None, repo=repo,
)
print("handler returned repaired =", repaired, "(git_pull maps this to GitPullResult.UP_TO_DATE)")
print("after: .git exists =", (root / ".git").exists(), "| working tree files kept =", sorted(p.name for p in root.rglob("*") if p.is_file()))
