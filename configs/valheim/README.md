# Valheim config

| File | What it controls |
| --- | --- |
| `server.env` | Settings shared by every world: server name, public listing, crossplay, admins and bans, updates, restarts, backups, mods. |
| `worlds/<name>.env` | One world each: its save name (`WORLD_NAME`) and its world modifiers (`SERVER_ARGS`). |
| `bepinex/plugins/` | BepInEx mods (`.dll` files or folders), loaded when `BEPINEX=true`. |

The password is not here: it is `VALHEIM_PASSWORD` in `images/valheim/.env`,
which is not in git.

## Worlds and modifiers

Each file in `worlds/` is one world. `VALHEIM_WORLD` in `images/valheim/.env`
picks which one runs (default: `default`). Switch for one run with:

```bash
VALHEIM_WORLD=hardcore docker compose -f images/valheim/docker-compose.yml up -d
```

Every world keeps its own save in `servers/valheim/config/worlds_local`, named
after its `WORLD_NAME`, so switching back and forth does not touch the other
world. To add a world, copy `worlds/default.env`, change `WORLD_NAME` and the
modifiers.

`SERVER_ARGS` holds the modifiers as the game's command-line arguments:

```
SERVER_ARGS=-preset hard -modifier raids none -setkey nomap
```

### `-preset <name>`

Sets every modifier at once. Put it first: modifiers after it override it.
`normal`, `casual`, `easy`, `hard` and `hardcore` match the difficulty presets
of the game's world screen. `immersive` is a harder, no-map game, and `hammer`
is a building mode (free building, passive enemies). Use `normal` to start from
the defaults.

### `-modifier <name> <value>`

One `-modifier` per setting. Leave a setting out to keep the preset's value.

| Name | Values | What it does |
| --- | --- | --- |
| `combat` | `veryeasy`, `easy`, `hard`, `veryhard` | Damage enemies deal and take. |
| `deathpenalty` | `casual`, `veryeasy`, `easy`, `hard`, `hardcore` | What you lose on death: `casual` keeps your items and skills, `hardcore` deletes the character. |
| `resources` | `muchless`, `less`, `more`, `muchmore`, `most` | How much drops from mining, chopping, enemies (0.5x to 3x). |
| `raids` | `none`, `muchless`, `less`, `more`, `muchmore` | How often raids hit your base. |
| `portals` | `casual`, `hard`, `veryhard` | `casual`: ores and metals can go through. `hard`: no portals to boss altars. `veryhard`: no portals at all. |

### `-setkey <key>`

| Key | What it does |
| --- | --- |
| `nobuildcost` | Building is free (you still need to discover recipes). |
| `playerevents` | Raids depend on each player's own progress, not the world's. |
| `passivemobs` | Enemies only attack when you attack them. |
| `nomap` | No map and no minimap. |

The modifiers are stored in the world save, and the server applies
`SERVER_ARGS` on every start, so a restart changes an existing world too.
Because the preset comes first and resets the modifiers, removing a `-modifier`
or `-setkey` should take it off again; check in game after such a change. A
misspelled name or value is ignored without an error.

`hardcore` death deletes characters. Back up first:
`servers/valheim/config/backups` has hourly backups from the hours people played.

## Mods

Set `BEPINEX=true` in `server.env` and put BepInEx plugins in
`bepinex/plugins/`. They are copied into the server on every start, and removed
from it when you delete them here. Plugin config files are written to
`servers/valheim/config/bepinex/config/`. Every player needs the same mods.
