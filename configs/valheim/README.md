# Valheim config

| File | What it controls |
| --- | --- |
| `server.env` | Settings for the server: name, public listing, crossplay, admins and bans, updates, restarts, backups, mods. |
| `world.env` | The world: its save name (`WORLD_NAME`) and its modifiers (`SERVER_ARGS`). |
| `bepinex/plugins/` | BepInEx mods (`.dll` files or folders), loaded when `BEPINEX=true`. |

The password is not here: it is `VALHEIM_PASSWORD` in `images/valheim/.env`,
which is not in git.

## The world and its seed

The server runs one world, set in `world.env`. Its save is
`servers/valheim/config/worlds_local/<WORLD_NAME>.fwl` and `.db`.

The seed is written into that save when the world is created. No documented
launch argument sets it, and `-seed` in `SERVER_ARGS` had no effect when tried.
To run a world with seed `epstein`:

1. In the Valheim game, create a new world named `funcompose` with seed `epstein`, and play a minute or two so it saves.
2. Copy `funcompose.fwl` and `funcompose.db` from `%USERPROFILE%\AppData\LocalLow\IronGate\Valheim\worlds_local` into `servers/valheim/config/worlds_local/`.
3. Start the server with `up -d`.

The name in step 1 has to match `WORLD_NAME`. If `worlds_local` already holds a
`funcompose` save, the server loads that one and it keeps its old seed. Move it
out of the folder first, or set a new `WORLD_NAME` for the new save.

## Modifiers

`SERVER_ARGS` holds the modifiers as the game's command-line arguments:

```
SERVER_ARGS=-preset normal -modifier resources muchmore
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

## Mods

Set `BEPINEX=true` in `server.env` and put BepInEx plugins in
`bepinex/plugins/`. They are copied into the server on every start, and removed
from it when you delete them here. Plugin config files are written to
`servers/valheim/config/bepinex/config/`. Every player needs the same mods.
