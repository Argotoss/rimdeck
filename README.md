# RimDeck

A mod manager and load-order sorter for RimWorld, for Windows, macOS and Linux.

RimDeck reads every mod's `About.xml`, sorts the active list with a topological sort over the mods' own load rules plus community and user rules, and manages Steam Workshop, SteamCMD, git and local mods.

## Status

Early development. The interface is being rebuilt and no releases have been published yet. The plan and its progress live in [docs/audit/milestones.md](docs/audit/milestones.md); the audit behind it is in [docs/audit/](docs/audit/README.md).

## Running from source

Requirements: git, Python 3.14, [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

```sh
git clone --recurse-submodules https://github.com/Argotoss/rimdeck
cd rimdeck
just dev-setup
uv run python -m app --dev
```

`--dev` keeps settings, logs and databases in a local `dev/` folder so a source run never touches an installed copy's data.

### Nix

The flake builds the app from `uv.lock` on Linux:

```sh
nix run github:Argotoss/rimdeck#rimdeck
nix develop
```

## Development

Project conventions, commands and the quality gate are in [AGENTS.md](AGENTS.md). Before committing, run:

```sh
just fix
just check
just test
```

## License

GPL-3.0. See [LICENSE.md](LICENSE.md).
