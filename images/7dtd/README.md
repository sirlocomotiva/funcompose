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

## Tune the game itself (zombies, hordes, loot, items)

`serverconfig.xml` covers the server settings. Everything else the game can be
tuned with lives in the game's own XML files under `Data/Config/` — 46 of them:
`spawning.xml` (zombies roaming in POIs and in the open), `gamestages.xml` (the
horde night, how fast it gets harder, horde loot), `loot.xml`, `items.xml`,
`blocks.xml`, `entitygroups.xml`, `buffs.xml` and more.

You keep those settings in this repo too. Put a file with the **same name** in
`configs/7dtd/Data/Config/`:

```
configs/7dtd/
├── serverconfig.xml                 # server settings (merged, see above)
├── Data/Config/
│   ├── spawning.xml                 # your zombie counts
│   └── gamestages.xml               # your horde-night tuning
└── Mods/
```

The file you commit is a **fragment**, not a copy of the game's file. On every
start each fragment is merged over the game's own file and the result replaces
it, so the server reads your values:

- only the values you list change, everything else keeps the default of the
  installed game version, so a game update will not drop your settings
- the game's own `<!-- comments -->` are kept, so the file still documents itself
- delete a fragment and the next start restores the game's own file

### Finding the values to change

After the first start, the game's own files with every property documented are
on disk:

```bash
less servers/7dtd/server/Data/Config/spawning.xml
less servers/7dtd/server/Data/Config/gamestages.xml
```

The merged result is written back to the same path, so you can also read your
own values there.

### How an element in your fragment is matched

Your element is looked up in the game's file, and the attributes you give are
set on it. It is found by, in order:

1. `match="attr=value,attr=value"` — use this when the element has no `name`.
   The file stops with an error if that does not pick exactly one element.
2. its `name` attribute
3. its `id` attribute
4. for an element that has children, all the attributes you wrote
5. for a single element, if it is the only one of its tag at that spot

`match=` is stripped from the output; the other attributes are written as they
are. A fragment can also **add** elements that the game does not have.

### Example: more zombies

```xml
<spawning>
	<entityspawner name="SpawnSmall">
		<day value="*">
			<property name="TotalAlive" value="10" />    <!-- alive at once -->
			<property name="TotalPerWave" value="18" />  <!-- released per wave -->
		</day>
	</entityspawner>
</spawning>
```

### Example: the horde night

The game computes a "game stage" for your party:

```
gameStage = (playerLevel + daysSurvived) * difficultyBonus
```

`daysSurvived` grows by 1 every game day and drops by
`daysAliveChangeWhenKilled` on each death, capped at your player level. The
horde then uses the `<gamestage stage="N">` block at or just below that number.
So these two values are the dials for how fast a horde grows:

```xml
<gamestages>
	<config difficultyBonus="1.0" daysAliveChangeWhenKilled="0" />
	<spawner name="BloodMoonHorde">
		<gamestage stage="13">
			<spawn match="group=feralHordeStageGS10,num=19" num="40" maxAlive="10" />
		</gamestage>
	</spawner>
</gamestages>
```

A group can appear more than once in the same stage, so `match=` needs enough
attributes to pick exactly one of them — here `num=19` is what makes the line
unique.

### If something does not match

- the container **stops** with an error when a selector is ambiguous, so it never
  silently changes the wrong element
- an unknown element name, or a `match=` that matches nothing, logs a `WARNING`
  and the element is added
- a fragment that is not valid XML stops the container before the game update,
  so you find out in seconds rather than after a 14 GB download

Remember that `--` is not allowed inside an XML comment.

### One thing to know

The merged file is written back out by an XML writer, so attributes that the
game had spread over several lines end up on one line. The content is the same
and all comments are kept, but do not expect the layout to be identical to the
file the game shipped. The game reads it, not you.

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
