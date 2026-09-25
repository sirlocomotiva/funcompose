# 7 Days to Die — standalone server image

A 7 Days to Die dedicated server that keeps your settings in git and applies them
on every start. This image is **not** used by the GameManager dashboard, which
creates 7DtD servers from `vinanrra/7dtd-server` (see `backend/games.py`).
Use it when you want the config-merge and repo-managed mods behaviour.

## Run it

```bash
docker compose -f images/7dtd/docker-compose.yml up -d --build
docker compose -f images/7dtd/docker-compose.yml logs -f 7dtd
```

The first start downloads the game (about 14 GB, 18 GB on disk). Later starts
only download updates.

## Configure it

Put your files in `configs/7dtd/`. The container applies them on **every** start:

| File | What happens on start |
| --- | --- |
| `serverconfig.xml` | Your properties are merged over the game's own default `serverconfig.xml`. Properties you do not list keep the default of the installed game version, so a game update does not lose settings. The result is `servers/7dtd/data/serverconfig.xml`. |
| `serveradmin.xml` (optional) | Replaces the server's admin file at `servers/7dtd/data/Saves/serveradmin.xml`. |
| `Mods/<ModName>/` (optional) | Each folder is copied into the game's `Mods` folder. Remove a folder from the repo and the mod is removed from the server. Mods bundled with the game are not changed. |

Apply a change with a restart:

```bash
docker compose -f images/7dtd/docker-compose.yml restart 7dtd
```

Notes:
- A typo in a property name logs a warning and the game ignores it. A broken XML file stops the container before the game update, so you find out in seconds.
- All properties and their descriptions are in `servers/7dtd/server/serverconfig.xml` after the first start.
- World settings (`GameWorld`, `WorldGenSeed`, `WorldGenSize`) and difficulty (`SandboxCode`) are stored in a save once it exists. Change `GameName` to start a new save.
- To manage admins in the repo: start the server once, copy `servers/7dtd/data/Saves/serveradmin.xml` to `configs/7dtd/serveradmin.xml`, then edit it. After that, admin, whitelist and ban changes made in the game are replaced on the next start.
- The container always sets `UserDataFolder=/data` and `TelnetEnabled=true`. Telnet is how it saves and stops the server cleanly. Without a `TelnetPassword`, telnet only listens inside the container.
- If you change `ServerPort`, also change the ports in `images/7dtd/docker-compose.yml`.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `SDTD_BRANCH` | `public` | Steam branch. `public` is the latest stable. Use for example `v3.2.0` to pin a version, or `latest_experimental`. |
| `SDTD_UPDATE` | `true` | Check for game updates on every start. |
| `SDTD_VALIDATE` | `false` | Verify all game files and repair them. Slow. |
| `PUID` / `PGID` | `1000` | Owner of the files in `servers/7dtd`. Use `0` to run as root (for example with rootless Podman). |
| `SDTD_ALLOW_EMULATION` | `false` | Start even when x86_64 is emulated. The current game version crashes there. |

## Console commands

```bash
docker compose -f images/7dtd/docker-compose.yml exec 7dtd sdtd cmd "say hello"
```

## x86_64 only

The game ships an x86_64 Linux server only, and it does not run under emulation.
Unity's Mono runtime aborts on both Rosetta and QEMU with:

```
Assertion at ../../mono/arch/amd64/../x86/x86-codegen.h:410, condition `offset == (gint32)offset' not met
```

The container detects this and stops before the 14 GB download. Run it on an
x86_64 Linux host. Set `SDTD_ALLOW_EMULATION=true` to skip the check.

## How it installs the game

The image uses [DepotDownloader](https://github.com/SteamRE/DepotDownloader)
3.4.0, not steamcmd: steamcmd is 32-bit and segfaults under emulation.
It downloads app `294420`, Linux depot `294422`, anonymously.
