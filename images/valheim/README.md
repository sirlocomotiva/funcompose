# Valheim — dedicated server

A Valheim dedicated server built on the community image
[`ghcr.io/community-valheim-tools/valheim-server`](https://github.com/community-valheim-tools/valheim-server-docker),
with the server settings and the world's modifiers kept in git.

## Run it

```bash
# 1. Set the password outside git
cp images/valheim/.env.example images/valheim/.env

# 2. Edit configs/valheim (server.env, world.env), commit it

# 3. Create and start the server
docker compose -f images/valheim/docker-compose.yml up -d
docker compose -f images/valheim/docker-compose.yml logs -f valheim
```

The first start downloads the game (about 1 GB) into `servers/valheim/server`.
The world is ready when the log shows `Game server connected`.

Apply a change to `configs/valheim` or `.env` with `up -d` again (a `restart`
does not reload env files). Players connect to `<host>:2456`, or find the server
by name in the community list when `SERVER_PUBLIC=true`.

## Configure it

See `configs/valheim/README.md` for the world's seed and modifiers, and for mods.

```
configs/valheim/
├── server.env            # name, public, crossplay, admins, updates, backups, mods
├── world.env             # save name (WORLD_NAME) and modifiers (SERVER_ARGS)
└── bepinex/plugins/      # BepInEx mods, when BEPINEX=true
images/valheim/.env       # VALHEIM_PASSWORD (not in git)
```

| Variable (in `images/valheim/.env`) | Default | Description |
| --- | --- | --- |
| `VALHEIM_PASSWORD` | required | Server password. At least 5 characters, and not part of `SERVER_NAME`. |

`server.env` passes its variables straight to the image, so every option in the
[image's README](https://github.com/community-valheim-tools/valheim-server-docker#environment-variables)
works there too (status page, supervisor UI, ValheimPlus, log filters, hooks).

## Files on disk

```
servers/valheim/
├── server/               # game files, updated automatically while nobody is online
└── config/
    ├── worlds_local/     # world saves: <WORLD_NAME>.fwl and .db
    ├── backups/          # zipped world backups, kept 3 days
    ├── adminlist.txt     # also bannedlist.txt, permittedlist.txt
    └── bepinex/config/   # mod config files written by the mods
```

To bring in a world from single player, copy its `.fwl` and `.db` from
`%USERPROFILE%\AppData\LocalLow\IronGate\Valheim\worlds_local` into
`servers/valheim/config/worlds_local/` and set `WORLD_NAME` to its file name
without the extension.

## Ports

Forward UDP 2456–2458 on your router for internet play. 2458 is only needed
with `CROSSPLAY=true`. If you change `SERVER_PORT`, change the ports in
`docker-compose.yml` too.

## x86_64 only

The image installs the game with steamcmd, a 32-bit x86 program. Docker on
Apple Silicon cannot run it (Rosetta has no 32-bit support), so run this on an
x86_64 Linux host.
