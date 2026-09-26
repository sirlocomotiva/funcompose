# 7 Days to Die — standalone server image

A 7 Days to Die dedicated server that keeps every game setting and your mods in
git and applies them on every start.

## Run it

```bash
# 1. Copy every config file the game ships into configs/7dtd (a few MB, ~10 s)
docker compose -f images/7dtd/docker-compose.yml run --rm pull

# 2. Edit what you want in configs/7dtd, commit it

# 3. Create and start the server
docker compose -f images/7dtd/docker-compose.yml up -d --build
docker compose -f images/7dtd/docker-compose.yml logs -f 7dtd
```

The first start downloads the game (about 14 GB, 18 GB on disk). Later starts
only download updates.

The repo already contains the files from the last pull, so step 1 is only
needed to refresh them (see [After a game update](#after-a-game-update)). The
pull only downloads config files and does not start the game, so it also works
on Apple Silicon, where the server itself cannot run.

## Configure it

`configs/7dtd/` holds a copy of every file you can configure:

```
configs/7dtd/
├── README.md             # what each file controls
├── serverconfig.xml      # server settings: name, slots, world, difficulty, ...
├── serveradmin.xml       # admins, whitelist, bans, command permissions
├── platform.cfg          # platforms and crossplay
├── Data/Config/          # the game's rules: zombies, hordes, loot, items, blocks, ...
│   ├── spawning.xml
│   ├── gamestages.xml
│   └── ...               # 59 files
├── Mods/                 # your mods, one folder each
└── .game-files.json      # written by the pull, do not edit
```

`configs/7dtd/README.md` says what each file controls. The container applies
them on **every** start:

| File | What happens on start |
| --- | --- |
| `serverconfig.xml` | The settings you changed are applied over the installed game's own `serverconfig.xml`. Settings you left alone keep the game's current default. The result is `servers/7dtd/data/serverconfig.xml`. |
| `serveradmin.xml` | Once you change it, it replaces the server's admin file at `servers/7dtd/data/Saves/serveradmin.xml`. Unchanged, the server keeps its own. |
| `Mods/<ModName>/` | Each folder is copied into the game's `Mods` folder. Remove a folder from the repo and the mod is removed from the server. Mods bundled with the game are not changed. |
| Every other file | Once you change it, your copy replaces the game's own (for example `servers/7dtd/server/Data/Config/spawning.xml`). Unchanged files are left alone. Undo your change or delete the file and the next start puts the game's copy back. |

"Changed" means the file differs from what the pull copied, as recorded in
`.game-files.json`. Line endings and a UTF-8 byte order mark do not count.

Apply a change with a restart:

```bash
docker compose -f images/7dtd/docker-compose.yml restart 7dtd
```

Notes:
- A typo in a property name logs a warning and the game ignores it. A broken XML file stops the container before the game update, so you find out in seconds.
- A changed game file must keep the game's root element, or the container stops. A file with less than half of the game's elements gets a warning, because it replaces the whole file: whatever is missing from it is missing from the game.
- World settings (`GameWorld`, `WorldGenSeed`, `WorldGenSize`) and difficulty (`SandboxCode`) are stored in a save once it exists. Change `GameName` to start a new save.
- The container always sets `UserDataFolder=/data` and `TelnetEnabled=true`. Telnet is how it saves and stops the server cleanly. Without a `TelnetPassword`, telnet only listens inside the container.
- If you change `ServerPort`, also change the ports in `images/7dtd/docker-compose.yml`.
- While your copy of a file is in place, the game's own copy is kept in `servers/7dtd/data/.sdtd-originals/`.

## After a game update

The server updates itself on start (`SDTD_UPDATE=true`). Your repo copies do not.
Files you did not change do not matter, because the server uses the game's
own copy of those. To bring the repo up to date, pull again and commit:

```bash
docker compose -f images/7dtd/docker-compose.yml run --rm pull
git status configs/7dtd
```

| File in the repo | What the pull does |
| --- | --- |
| unchanged, and the game changed it | replaced with the game's new version |
| changed by you | kept. If the game changed it too, you get a warning |
| new in the game | added |
| gone from the game | deleted if you did not change it, otherwise kept with a warning |
| `serverconfig.xml` | rewritten from the game's new file, with the settings you changed filled in. Settings you left at the default take the game's new default. Your own comments in the file are not kept. |

A changed file is a whole file, so it does not pick up what the game changed in
it. The pull, and every start, warns when that happens. To move to the new
version, delete your copy, pull again, and make your changes again. `git diff`
shows them.

Pull with the same `SDTD_BRANCH` the server runs. The container warns if they differ.

## Change a game file without copying it: modlets

The game can patch its own files from a mod folder with XPath. Such a modlet
holds only your changes, so it keeps working when the game updates the file. Use
it for changes you want to survive updates without a manual merge. Leave the
full copy in `Data/Config` unchanged if you do.

```
configs/7dtd/Mods/funcompose-tuning/
├── ModInfo.xml
└── Config/
    └── gamestages.xml
```

`ModInfo.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xml>
	<Name value="funcompose-tuning" />
	<DisplayName value="funcompose tuning" />
	<Description value="Server tuning kept in the funcompose repo" />
	<Author value="you" />
	<Version value="1.0.0" />
	<Website value="" />
</xml>
```

`Config/gamestages.xml`:

```xml
<configs>
	<set xpath="/gamestages/config/@difficultyBonus">1.0</set>
	<set xpath="/gamestages/config/@daysAliveChangeWhenKilled">0</set>
</configs>
```

`Data/Config/XML.txt` in the repo is the developers' reference for these files.

## Tuning zombies and hordes

`spawning.xml`: each `<entityspawner>` is a spawn point. `TotalAlive` is how
many of that kind may be alive at the same time, `TotalPerWave` how many are
released per wave. `SpawnExtraSmall` to `SpawnExLarge` spawn from the
`ZombiesAll` group, 2 to 12 alive at once by default. The biome sections at the
top of the file set what roams in the open.

`gamestages.xml`: the game computes a "game stage" for your party:

```
gameStage = (playerLevel + daysSurvived) * difficultyBonus
```

`daysSurvived` grows by 1 every game day and drops by
`daysAliveChangeWhenKilled` on each death, capped at your player level. The
horde then uses the `<gamestage stage="N">` block of `<spawner
name="BloodMoonHorde">` at or just below that number. Each `<spawn>` in it is
one group: `num` is how many zombies it sends (999 means until the stage time
is up), `maxAlive` how many of them may be alive at once, per player. So
`difficultyBonus` and `daysAliveChangeWhenKilled` in `<config>` decide how fast
hordes grow, and `maxAlive` decides whether the server keeps up.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `SDTD_BRANCH` | `public` | Steam branch. `public` is the latest stable. Use for example `v3.2.0` to pin a version, or `latest_experimental`. Used by the server and by the pull. |
| `SDTD_UPDATE` | `true` | Check for game updates on every start. |
| `SDTD_VALIDATE` | `false` | Verify all game files and repair them. Slow. |
| `PUID` / `PGID` | `1000` | Owner of the files in `servers/7dtd`, and of the files the pull writes to `configs/7dtd`. Use `0` to run as root (for example with rootless Podman on Linux). |
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
x86_64 Linux host. Set `SDTD_ALLOW_EMULATION=true` to skip the check. The pull
does not run the game, so it works anywhere.

## How it installs the game

The image uses [DepotDownloader](https://github.com/SteamRE/DepotDownloader)
3.4.0, not steamcmd: steamcmd is 32-bit and segfaults under emulation.
It downloads app `294420`, Linux depot `294422`, anonymously. The pull uses the
same depot with a file list, so it only downloads the config files.
