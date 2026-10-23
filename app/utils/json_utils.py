import json
import os
import stat
import sys
import tempfile
import time
from typing import Any

from loguru import logger

_REPLACE_ATTEMPTS = 5
_REPLACE_RETRY_DELAY = 0.05


def _clear_read_only_flag(destination: str) -> bool:
    """Clear the read-only attribute of a destination file on Windows.

    Windows refuses to replace a read-only file with ``PermissionError``
    (``[WinError 5] Access is denied``), no matter whether RimDeck runs
    elevated. Clearing the attribute is best effort, so a destination that is
    locked instead of read-only keeps failing and surfaces the original error.
    The cleared attribute is logged so the change stays visible.

    :param destination: Path of the file that is about to be replaced
    :return: True if the read-only attribute was cleared, False otherwise
    """
    if sys.platform != "win32":
        return False

    try:
        mode = os.stat(destination).st_mode
        if mode & stat.S_IWRITE:
            return False
        os.chmod(destination, mode | stat.S_IWRITE)
    except OSError:
        return False

    logger.warning(
        f"Cleared the read-only attribute of {destination} so it can be written"
    )
    return True


def _replace_with_retry(source: str, destination: str) -> None:
    """Replace a file, tolerating short-lived Windows file locks."""
    attempt = 0
    cleared_read_only = False
    while True:
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            # A read-only destination can never be replaced, so clearing the
            # attribute is not a retry: it is tried again right away, which
            # leaves the lock backoff budget untouched.
            if not cleared_read_only and _clear_read_only_flag(destination):
                cleared_read_only = True
                continue
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_RETRY_DELAY * 2**attempt)
            attempt += 1


def atomic_write_text(text: str, path: str, suffix: str = "") -> None:
    """Write text so that ``path`` holds either the old or the new content.

    The text goes to a temporary file in the same directory, is flushed to
    disk, then replaces ``path`` in one step, so a crash mid-write can't leave
    a truncated file behind.

    :param text: Content to write (UTF-8).
    :param path: Destination file.
    :param suffix: Suffix for the temporary file.
    """
    dirpath = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(suffix=suffix, dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(fd)
        _replace_with_retry(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def atomic_json_dump(data: Any, path: str, **kwargs: Any) -> None:
    atomic_write_text(json.dumps(data, **kwargs), path, suffix=".json")
