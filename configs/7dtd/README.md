# 7 Days to Die config

Everything here is a copy of a file the game ships, fetched with:

```bash
docker compose -f images/7dtd/docker-compose.yml run --rm pull
```

Edit any of them before you create the server (or at any time later) and start
it with `docker compose -f images/7dtd/docker-compose.yml up -d --build`.

- A file you **changed** replaces the game's own copy on every start.
- A file you did **not** change is ignored, so the server uses the installed
  game version's file. Undo your change or delete the file and the game's copy
  is back on the next start.
- `serverconfig.xml` is the exception: only the settings you changed are
  applied, over the defaults of the installed game version.
- `.game-files.json` records what each file looked like when the game shipped
  it. That is how the container tells your changes apart. Commit it with the
  files, and do not edit it.

After a game update, run the pull again. It updates the files you did not
change and keeps the ones you did. See `images/7dtd/README.md` for the details.

## What each file controls

### Server

| File | What it controls |
| --- | --- |
| `serverconfig.xml` | The server: name, password, slots, ports, world and seed, difficulty, day length, blood moon frequency, loot amount, land claims, drops on death. Every setting has its description next to it. |
| `serveradmin.xml` | Admins, whitelist, bans, command permission levels, web API tokens. See the note below. |
| `platform.cfg` | The platforms the server registers with (Steam, crossplay through EOS, Xbox, PlayStation). |

### Zombies, animals and hordes

| File | What it controls |
| --- | --- |
| `Data/Config/spawning.xml` | Roaming spawns per biome and in POIs: how many zombies and animals are alive at once and how many come per wave (`TotalAlive`, `TotalPerWave`). |
| `Data/Config/gamestages.xml` | The game stage formula (`difficultyBonus`, `daysAliveChangeWhenKilled`), the blood moon horde and wandering hordes for every stage, horde loot bonus. |
| `Data/Config/entitygroups.xml` | Which zombie and animal types make up each spawn group, and how likely each one is. |
| `Data/Config/entityclasses.xml` | Zombies, animals, the player: health, speed, damage, what they drop. |
| `Data/Config/npc.xml` | Traders and other NPCs, and the factions they belong to. |
| `Data/Config/utilityai.xml` | How NPCs decide what to do. |
| `Data/Config/archetypes.xml` | Character presets for players and NPCs (looks and gear). |

### Items, crafting and loot

| File | What it controls |
| --- | --- |
| `Data/Config/items.xml` | Every item, tool, weapon and food: damage, durability, stack size, effects. |
| `Data/Config/item_modifiers.xml` | Weapon and tool mods, and cosmetic mods. |
| `Data/Config/recipes.xml` | What can be crafted, from what, and where (backpack, workbench, forge, ...). |
| `Data/Config/loot.xml` | What every container, corpse and loot bag can contain, and how much. |
| `Data/Config/traders.xml` | Trader stock, prices, restock timers, trader opening hours. |
| `Data/Config/qualityinfo.xml` | The colors of the quality tiers. |
| `Data/Config/misc.xml` | Weapon carry and hold types. |

### Player

| File | What it controls |
| --- | --- |
| `Data/Config/progression.xml` | Levels, XP, skill points, attributes, perks and books. |
| `Data/Config/buffs.xml` | Every status effect: food and water, health, infections, stamina, temperature, drugs, perk effects. |
| `Data/Config/challenges.xml` | The challenges list. |
| `Data/Config/quests.xml` | Trader quests and their rewards, the intro quests. |
| `Data/Config/dialogs.xml` | Trader and NPC dialogs. |
| `Data/Config/Stealth.txt` | Notes from the developers on how stealth works (sight, noise, smell). For reading. |

### World and blocks

| File | What it controls |
| --- | --- |
| `Data/Config/blocks.xml` | Every block: health, upgrade paths, what it drops when destroyed or harvested, farming. |
| `Data/Config/shapes.xml` | The block shapes (ramps, poles, plates, ...) available for each material. |
| `Data/Config/materials.xml` | Block materials: hardness, stability, sounds. |
| `Data/Config/blockplaceholders.xml` | Random blocks in POIs that turn into one of a list of blocks (cars, loot, ...). |
| `Data/Config/biomes.xml` | Biomes: weather, temperature, what grows and which ores are in the ground. |
| `Data/Config/rwgmixer.xml` | Random world generation: towns, POI placement, roads, terrain. |
| `Data/Config/worldglobal.xml` | Global lighting, sky and environment values. |
| `Data/Config/weathersurvival.xml` | Extra temperature per height. |
| `Data/Config/vehicles.xml` | Vehicles: speed, fuel use, storage, seats. |
| `Data/Config/painting.xml` | The textures you can paint blocks with. |
| `Data/Config/signs.xml` | Icons and colors for signs. |
| `Data/Config/physicsbodies.xml` | Ragdoll and physics setup for bodies. |
| `Data/Config/nav_objects.xml` | Map, compass and screen markers. |
| `Data/Config/sandbox_overrides.xml` | Your own sandbox (difficulty) presets, and sandbox options to lock at their default. The file lists every option. |
| `Data/Config/events.xml` | Dated events, for example seasonal holidays. |
| `Data/Config/BlockUpdates.csv` | Old block names and what they were converted to, for older saves. |
| `Data/Config/OversizedConversionTargets.txt` | Block names the game uses when it converts oversized blocks. Internal. |

### Twitch integration

| File | What it controls |
| --- | --- |
| `Data/Config/twitch.xml` | Twitch actions viewers can trigger, their costs and cooldowns. |
| `Data/Config/twitch_events.xml` | Twitch events (follows, subs, raids) and what they trigger. |
| `Data/Config/gameevents.xml` | The game events used by Twitch actions and other scripted events. |

### Sound, UI and text

| File | What it controls |
| --- | --- |
| `Data/Config/sounds.xml` | Every sound: volume, range, how far zombies can hear it. |
| `Data/Config/music.xml`, `Data/Config/dmscontent.xml` | Dynamic music. |
| `Data/Config/subtitles.xml` | Subtitles for voice lines. |
| `Data/Config/ui_display.xml` | How item and block stats are shown in the UI. |
| `Data/Config/loadingscreen.xml` | Loading screen images and tips. |
| `Data/Config/videos.xml` | Video list (empty in the game). |
| `Data/Config/XUi_Common/`, `XUi_InGame/`, `XUi_Menu/` | The user interface: windows, templates, styles. |
| `Data/Config/Localization.csv` | Every text in the game, in every language: item names, descriptions, messages. |
| `Data/Config/XML.txt` | The developers' notes on the XML files. For reading. |

## serveradmin.xml

The game writes its own admin file on the first start. The copy here lets you
set up admins, the whitelist and bans before that.

As long as you do not change it, the server keeps its own admin file, and
changes made in the game ("admin add", "ban add", the web dashboard) stay. Once
you change it, it replaces the server's admin file on every start, and changes
made in the game are lost on the next start.

## Mods

Put each mod in its own folder under `Mods/`. It is copied into the game on
every start, and removed from the server when you delete it here.

A mod is also the way to change a game file without replacing it: a modlet with
only your changes keeps working when the game updates the file. See
`images/7dtd/README.md`.
