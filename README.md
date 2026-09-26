# funcompose

A 7 Days to Die dedicated server in Docker, with every game setting and your
mods kept in git.

## Quick start

```bash
# optional: refresh the copies of the game's config files in configs/7dtd
docker compose -f images/7dtd/docker-compose.yml run --rm pull

# edit configs/7dtd, commit, then create and start the server
docker compose -f images/7dtd/docker-compose.yml up -d --build
docker compose -f images/7dtd/docker-compose.yml logs -f 7dtd
```

The first start downloads the game (about 14 GB, 18 GB on disk) into
`servers/7dtd/`. Later starts only download updates.

## How it works

- `configs/7dtd/` holds a copy of **every file you can configure**: `serverconfig.xml`, `serveradmin.xml`, `platform.cfg` and all 59 files in `Data/Config` (zombies, hordes, loot, items, blocks, traders, progression, ...). Edit them before you create the server. `configs/7dtd/README.md` says what each one controls.
- On every start, a file you changed replaces the game's own copy. Files you did not change are left alone, and undoing a change or deleting the file brings the game's copy back. For `serverconfig.xml` only the settings you changed are applied; the result is written to `servers/7dtd/data/serverconfig.xml`.
- `pull` downloads just those files (a few MB) with the same Steam branch as the server, so it also works on Apple Silicon. After a game update, run it again: it updates the files you did not change and keeps the ones you did.
- Each folder in `configs/7dtd/Mods/` is copied into the game. A folder you delete from the repo is removed from the server. Mods bundled with the game are not touched.
- Apply your changes with `docker compose -f images/7dtd/docker-compose.yml restart 7dtd`. Send one console command with `... exec 7dtd sdtd cmd "say hello"`.
- On stop the container asks the server to save the world over telnet before shutting down.

For internet play, forward port 26900 (TCP and UDP) and 26901–26903 (UDP) on
your router.

This image needs an **x86_64** host. The game's Mono runtime aborts under
Rosetta and under QEMU, so the container stops before the ~14 GB download on
Apple Silicon or other ARM hosts. Set `SDTD_ALLOW_EMULATION=true` to skip that
check.

See `images/7dtd/README.md` for all options, what happens after a game update,
and how to tune zombie spawns and horde size.

## Layout

```
configs/7dtd/     your settings and mods (in git)
images/7dtd/      the server image and its compose file
servers/7dtd/     game files, saves and worlds (not in git)
```
