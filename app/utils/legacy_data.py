"""One-time import of data from the app RimDeck was originally based on.

On the first launch without a settings file, the original app's data folder
(settings, databases, mod lists, instances, backups) is copied into RimDeck's
own data folder. The original folder is never modified. Paths inside the
copied ``settings.json`` that pointed into the old folder are rewritten to the
new one so instances keep working.
"""

import json
import shutil
from pathlib import Path

from loguru import logger
from platformdirs import PlatformDirs

LEGACY_APP_NAME = "RimSort"
SETTINGS_FILE_NAME = "settings.json"


def legacy_data_folder() -> Path:
    """Return the original app's data folder on this platform."""
    return Path(PlatformDirs(appname=LEGACY_APP_NAME, appauthor=False).user_data_dir)


def _rewrite_paths(value: object, old_prefix: str, new_prefix: str) -> object:
    if isinstance(value, str) and value.startswith(old_prefix):
        return new_prefix + value[len(old_prefix) :]
    if isinstance(value, list):
        return [_rewrite_paths(item, old_prefix, new_prefix) for item in value]
    if isinstance(value, dict):
        return {
            key: _rewrite_paths(item, old_prefix, new_prefix)
            for key, item in value.items()
        }
    return value


def import_legacy_data(new_folder: Path, legacy_folder: Path) -> bool:
    """Copy the original app's data into ``new_folder`` if it has none yet.

    :param new_folder: RimDeck's data folder.
    :param legacy_folder: The original app's data folder.
    :return: True if data was imported.
    """
    if (new_folder / SETTINGS_FILE_NAME).exists():
        return False
    legacy_settings = legacy_folder / SETTINGS_FILE_NAME
    if not legacy_settings.is_file():
        return False

    logger.info(f"Importing data from {legacy_folder} into {new_folder}")
    try:
        shutil.copytree(
            legacy_folder,
            new_folder,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.lock"),
        )
        settings_path = new_folder / SETTINGS_FILE_NAME
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings = _rewrite_paths(settings, str(legacy_folder), str(new_folder))
        settings_path.write_text(json.dumps(settings, indent=4), encoding="utf-8")
    except OSError, ValueError:
        logger.exception("Importing data from the original app failed")
        # A half-copied settings file would block a clean first run.
        (new_folder / SETTINGS_FILE_NAME).unlink(missing_ok=True)
        return False
    logger.info("Imported data from the original app")
    return True
