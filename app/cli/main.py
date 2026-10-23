"""
Main CLI entry point for RimDeck.

This module defines the Click command group and registers all subcommands.
"""

import click

from app.cli.build_db import build_db
from app.utils.app_info import AppInfo


@click.group()
@click.version_option(version=AppInfo().app_version, prog_name="RimDeck")
def cli() -> None:
    """RimDeck - RimWorld mod manager CLI

    Headless tools for managing RimWorld mods, building databases, and more.

    Global flags (processed before CLI):
      --disable-updater    Disable automatic update checks (same as RIMDECK_DISABLE_UPDATER env var)
    """


# Register subcommands
cli.add_command(build_db)


if __name__ == "__main__":
    cli()
