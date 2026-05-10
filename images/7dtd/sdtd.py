#!/usr/bin/env python3
"""Run a 7 Days to Die dedicated server with configs from the funcompose repo.

Commands:
  sdtd run          Install or update the game, apply /config, start the server.
  sdtd pull         Copy every config file the game ships into /config, so you
                    can edit them before the first start. Run it again after a
                    game update: files you did not change are updated, files
                    you changed are kept.
  sdtd cmd <text>   Send one console command to the running server over telnet.
  sdtd sandbox      Print the sandbox code that /config/sandbox.xml makes.
  sdtd sandbox <code>
                    Write the options of a sandbox code (from the game's Sandbox
                    Options screen) into /config/sandbox.xml.

On every start, "run" applies the repo configs that are mounted at /config:
  serverconfig.xml  The settings you changed are applied over the game's
                    default file. The result is written to /data/serverconfig.xml.
  sandbox.xml       Turned into the SandboxCode setting of serverconfig.xml.
  serveradmin.xml   Once you change it, it replaces the server's admin file.
  Mods/<name>/      Each folder is copied into the game's Mods folder.
                    A mod that you remove from the repo is removed from the server.
  Any other file    A copy of a game file (Data/Config/*.xml, platform.cfg, ...).
                    Once you change it, it replaces the game's own copy. Undo the
                    change or delete the file and the game's copy is back on the
                    next start.
"""

import codecs
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, unescape

SERVER_DIR = "/server"
DATA_DIR = "/data"
CONFIG_DIR = "/config"
HOME_DIR = os.environ.get("HOME", "/home/sdtd")

APP_ID = "294420"
LINUX_DEPOT_ID = "294422"
DEPOT_DOWNLOADER = "/opt/depotdownloader/DepotDownloader"
SERVER_BINARY = "7DaysToDieServer.x86_64"
MANAGED_MODS_FILE = ".funcompose-managed-mods.json"
# What "sdtd pull" copies from the game, in DepotDownloader's -filelist syntax.
PULL_FILE_LIST = ["serverconfig.xml", "platform.cfg", "regex:^Data/Config/"]
# The game writes serveradmin.xml on the first start. This is the same file,
# so it can be edited before that.
ADMIN_TEMPLATE = "/usr/local/share/sdtd/serveradmin.xml"
# Written by "sdtd pull" into /config: each file's hash as the game shipped it,
# which is how "run" tells the files you changed from the ones you did not.
PULLED_STATE_FILE = ".game-files.json"
# Sandbox options (loot, XP, zombies, traders, ...) by name. The game only reads them
# as one SandboxCode setting, so "run" builds that code from this file.
SANDBOX_FILE = "sandbox.xml"
SANDBOX_CODE_VERSION = "A"
# Entries in /config that are not plain copies of game files.
NOT_GAME_FILES = ("serverconfig.xml", "serveradmin.xml", SANDBOX_FILE, "Mods")
# The game's own copies of the files you replaced, so a change can be undone.
ORIGINALS_SUBDIR = ".sdtd-originals"
ORIGINALS_STATE_FILE = ".state.json"
LEGACY_STATE_FILE = "applied.json"  # from the old fragment merge

PROPERTY_PATTERN = re.compile(r'(<property\s+name="([^"]+)"\s+value=")([^"]*)(")')
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

# The container layout needs these values, so they win over the repo config.
FORCED_PROPERTIES = {
    "UserDataFolder": DATA_DIR,  # saves and generated worlds go to the /data volume
    "TelnetEnabled": "true",  # needed to stop the server cleanly and for "sdtd cmd"
}

STOP_TIMEOUT_SECONDS = 90


def log(message):
    print(f"[sdtd] {message}", flush=True)


def fail(message):
    log(f"ERROR: {message}")
    sys.exit(1)


def env_flag(name, default):
    value = os.environ.get(name, default).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    fail(f"{name} must be true or false, not {value!r}")


def game_branch():
    return os.environ.get("SDTD_BRANCH", "public").strip() or "public"


# --- files ------------------------------------------------------------------


def content_hash(path):
    """Hash a file, ignoring a UTF-8 byte order mark and CRLF vs LF line ends.

    Git and editors change those without changing what the file says, and the
    game ships a mix of both.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8):]
    return hashlib.sha1(data.replace(b"\r\n", b"\n")).hexdigest()


def walk_files(top, skip=()):
    """Relative paths (with "/") of the files under top. Hidden entries are left out."""
    found = []
    for root, dirs, files in os.walk(top):
        prefix = os.path.relpath(root, top).replace(os.sep, "/")
        prefix = "" if prefix == "." else prefix + "/"
        dirs[:] = [name for name in dirs if not name.startswith(".") and prefix + name not in skip]
        found.extend(prefix + name for name in files
                     if not name.startswith(".") and prefix + name not in skip)
    return sorted(found)


def copy_file(source, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)


def remove_file(top, rel):
    """Delete top/rel, and then its folders if that left them empty."""
    top = os.path.normpath(top)
    path = os.path.join(top, rel)
    os.remove(path)
    parent = os.path.dirname(path)
    while len(parent) > len(top) and not os.listdir(parent):
        os.rmdir(parent)
        parent = os.path.dirname(parent)


def read_json(path, default):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def read_pulled_state(config_dir):
    """What the last "sdtd pull" recorded, or None if it never ran."""
    path = os.path.join(config_dir, PULLED_STATE_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as handle:
            state = json.load(handle)
        if not isinstance(state.get("files"), dict):
            raise ValueError('it has no "files" entry')
    except (OSError, ValueError, AttributeError) as error:
        fail(f'{path} is damaged ({error}). Restore it from git, or delete it and run "sdtd pull".')
    return state


def pulled_files(pulled):
    return pulled["files"] if pulled else {}


def changed_files(config_dir, pulled):
    """The copies of game files in /config that differ from what the game shipped."""
    shipped = pulled_files(pulled)
    return [
        rel for rel in walk_files(config_dir, skip=NOT_GAME_FILES)
        if not rel.endswith(".md") and shipped.get(rel) != content_hash(os.path.join(config_dir, rel))
    ]


def admin_file_changed(config_dir, pulled):
    source = os.path.join(config_dir, "serveradmin.xml")
    if not os.path.isfile(source):
        return False
    return pulled_files(pulled).get("serveradmin.xml") != content_hash(source)


# --- serverconfig.xml -------------------------------------------------------


def parse_xml(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        return ET.parse(path, parser)
    except ET.ParseError as error:
        fail(f"{path} is not valid XML: {error}. Fix the file and restart the container.")


def read_properties(tree, path, root_tag="ServerSettings"):
    root = tree.getroot()
    if root.tag != root_tag:
        fail(f"{path}: the root element must be <{root_tag}>, not <{root.tag}>")
    properties = {}
    for element in root.iter("property"):
        name = element.get("name")
        value = element.get("value")
        if not name or value is None:
            fail(f"{path}: every <property> needs a name and a value attribute")
        properties[name] = value
    return properties


def merge_server_config(default_path, overrides_path, output_path, pulled_defaults, generated=None):
    """Write the game's default config with the repo properties applied.

    A property that still has the value "sdtd pull" copied from the game is
    left alone, so the game's current default applies to it. generated holds
    properties made from other repo files, which win over serverconfig.xml.
    Returns the effective properties.
    """
    generated = generated or {}
    tree = parse_xml(default_path)
    root = tree.getroot()
    elements = {element.get("name"): element for element in root.iter("property")}

    overrides = {}
    if os.path.isfile(overrides_path):
        overrides = read_properties(parse_xml(overrides_path), overrides_path)
    else:
        log(f"No {overrides_path}; using the game's default settings.")

    applied = 0
    for name, value in overrides.items():
        if name in pulled_defaults and pulled_defaults[name] == value:
            continue
        if name in FORCED_PROPERTIES and value != FORCED_PROPERTIES[name]:
            log(f"WARNING: {name} is managed by the container; ignoring your value {value!r}.")
            continue
        if name in generated:
            if value != generated[name]:
                log(f"WARNING: ignoring {name} in serverconfig.xml: {SANDBOX_FILE} sets it. "
                    f'To use that code, run "sdtd sandbox {value}" or delete {SANDBOX_FILE}.')
            continue
        if name not in elements:
            log(f"WARNING: {name} is not in the game's default serverconfig.xml. Check the spelling.")
        set_property(root, elements, name, value)
        applied += 1

    for name, value in list(generated.items()) + list(FORCED_PROPERTIES.items()):
        set_property(root, elements, name, value)

    notice = ET.Comment(
        " GENERATED FILE. Do not edit. Edit configs/7dtd/serverconfig.xml in the repo"
        " and restart the container. "
    )
    notice.tail = "\n\n\t"
    root.insert(0, notice)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    log(f"Applied {applied} setting(s) you changed in {overrides_path} -> {output_path}")
    return {element.get("name"): element.get("value") for element in root.iter("property")}


def set_property(root, elements, name, value):
    element = elements.get(name)
    if element is None:
        if len(root):
            root[-1].tail = "\n\t"
        element = ET.SubElement(root, "property", {"name": name, "value": value})
        element.tail = "\n"
        elements[name] = element
    element.set("value", value)


def quote_attribute(value):
    return escape(value, {'"': "&quot;"})


def write_full_server_config(game_path, values, old_defaults, output_path):
    """Write the game's whole serverconfig.xml, comments included, with your values in it.

    The text is edited in place rather than rewritten by an XML library, so the
    file keeps the game's layout and a later pull shows only real changes. A value
    that still equals the game's old default takes the game's new default.
    Returns the game's defaults and the number of settings that differ from them.
    """
    with open(game_path, "rb") as handle:
        data = handle.read()
    bom = data.startswith(codecs.BOM_UTF8)
    text = data[len(codecs.BOM_UTF8):] if bom else data
    text = text.decode("utf-8")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")

    # The file shows extra properties as commented-out examples. Leave those alone.
    comments = [match.span() for match in COMMENT_PATTERN.finditer(text)]
    yours = {name: value for name, value in values.items() if old_defaults.get(name) != value}
    defaults = {}
    placed = set()

    def fill(match):
        if any(start <= match.start() < end for start, end in comments):
            return match.group(0)
        name = match.group(2)
        default = unescape(match.group(3), {"&quot;": '"', "&apos;": "'"})
        defaults.setdefault(name, default)
        if name not in yours or name in placed:
            return match.group(0)
        placed.add(name)
        if yours[name] == default:
            return match.group(0)
        return match.group(1) + quote_attribute(yours[name]) + match.group(4)

    text = PROPERTY_PATTERN.sub(fill, text)

    missing = [name for name in yours if name not in placed]
    if missing:
        end = text.rfind("</ServerSettings>")
        if end < 0:
            fail(f"{game_path} has no </ServerSettings>.")
        extra = "".join(
            f'\t<property name="{quote_attribute(name)}" value="{quote_attribute(yours[name])}"/>\n'
            for name in missing
        )
        text = text[:end] + extra + text[end:]
        for name in missing:
            log(f"WARNING: serverconfig.xml: the game has no {name} setting. Your value is kept at "
                "the end of the file. Remove it if it is a typo or the game dropped the setting.")

    if crlf:
        text = text.replace("\n", "\r\n")
    output = text.encode("utf-8")
    if bom:
        output = codecs.BOM_UTF8 + output
    old = None
    if os.path.isfile(output_path):
        with open(output_path, "rb") as handle:
            old = handle.read()
    if output != old:
        with open(output_path, "wb") as handle:
            handle.write(output)
    changed = len([name for name in placed if yours[name] != defaults[name]]) + len(missing)
    return defaults, changed


# --- serveradmin.xml and Mods -----------------------------------------------


def apply_admin_file(config_dir, data_dir, admin_file_name, pulled):
    """Replace the server's admin file with the repo's, once you changed the repo's."""
    source = os.path.join(config_dir, "serveradmin.xml")
    if not admin_file_changed(config_dir, pulled):
        return
    parse_xml(source)  # stop early if the file is broken
    target = os.path.join(data_dir, "Saves", admin_file_name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)
    log(f"Applied {source} -> {target}")


def sync_mods(config_mods_dir, server_mods_dir):
    """Copy each repo mod folder into the game. Remove repo mods that are gone."""
    os.makedirs(server_mods_dir, exist_ok=True)
    state_path = os.path.join(server_mods_dir, MANAGED_MODS_FILE)

    previous = []
    if os.path.isfile(state_path):
        with open(state_path) as state_file:
            previous = json.load(state_file)

    current = []
    if os.path.isdir(config_mods_dir):
        for name in sorted(os.listdir(config_mods_dir)):
            path = os.path.join(config_mods_dir, name)
            if name.startswith("."):
                continue
            if not os.path.isdir(path):
                log(f"WARNING: skipping {path}: a mod must be a folder. Extract archives first.")
                continue
            current.append(name)

    for name in previous:
        if name not in current:
            shutil.rmtree(os.path.join(server_mods_dir, name), ignore_errors=True)
            log(f"Removed mod {name} (not in the repo anymore)")

    for name in current:
        target = os.path.join(server_mods_dir, name)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(os.path.join(config_mods_dir, name), target)
        log(f"Installed mod {name}")

    with open(state_path, "w") as state_file:
        json.dump(current, state_file)


# --- sandbox.xml ------------------------------------------------------------


def percent(*values):
    return tuple(f"{value}%" for value in values)


# The values of each sandbox option, in the game's order: a code stores the position.
SANDBOX_VALUES = {
    "DamageValues": percent(0, 25, 35, 50, 65, 75, 85, 100, 125, 150, 200, 250, 300),
    "DamageValuesNoNone": percent(25, 35, 50, 65, 75, 85, 100, 125, 150, 200, 250, 300),
    "PlayerSpeedValues": percent(0, 25, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 200, 300),
    "PlayerSpeedValuesWithNone": percent(25, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 200, 300),
    "SpeedValues": percent(0, 25, 50, 75, 100, 125, 150, 200, 300),
    "StaminaUsage": percent(0, 25, 50, 75, 100, 125, 150, 175, 200),
    "LootAbundanceValues": percent(0, 25, 35, 50, 65, 75, 85, 100, 125, 150, 200, 300, 400, 500),
    "ZombieRageChance": percent(0, 15, 30, 35, 40, 50, 60, 75, 90, 100),
    "ZombieSpeeds": ("walk", "jog", "run", "sprint", "nightmare"),
    "AISmellMode": ("none", "walk", "jog", "run", "sprint", "nightmare"),
    "JumpStrength": percent(0, 50, 100, 125, 150, 200, 300),
    "StaminaRegen": percent(25, 50, 75, 100, 125, 150, 200, 300),
    "XPGain": percent(0, 25, 50, 75, 100, 125, 150, 175, 200, 300, 500),
    "JarRefund": percent(0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
    "BarterValues": percent(0, 25, 50, 75, 100, 125, 150, 175, 200, 300, 400),
    "DisabledLowDefaultHigh": ("disabled", "very low", "low", "default", "high", "very high"),
    "LowDefaultHigh": ("very low", "low", "default", "high", "very high"),
    "Encumbrance": ("disabled", "low", "default", "high", "very high", "full"),
    "SkillGainRate": ("1", "2", "3", "4", "5"),
    "PointsPer": ("0", "1", "2", "3", "4", "5", "6", "7"),
    "StarterSkillPoints": ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
    "BloodMoonFrequency": ("disabled", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "14", "20", "30"),
    "BloodMoonRange": ("0", "1", "2", "3", "4", "7", "10", "14", "20"),
    "BloodMoonWarning": ("disabled", "morning", "evening"),
    "BloodMoonCount": ("4", "6", "8", "10", "12", "16", "24", "32", "64"),
    "AirDrops": ("disabled", "1", "1-3", "3", "3-7", "7", "1-7"),
    "AirDropRandomTime": ("none", "morning", "mid day", "evening", "night", "all day", "any"),
    "StormFrequency": percent(0, 50, 100, 150, 200, 300, 400, 500),
    "QuestPerTier": ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"),
    "QuestPerDay": ("unlimited", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
    "TraderArea": ("yes", "claimable", "not claimable"),
    "TraderResetInterval": ("default", "1", "2", "3", "4", "5", "6", "7", "14"),
    "ItemTierOptions": ("default", "1", "2", "3", "4", "5", "6"),
    "DewCollectorInput": percent(0, 100, 200, 300),
    "ApiaryInput": percent(0, 20, 40, 60, 80, 100, 150, 200, 300),
    "CollectorOutput": percent(100, 200, 300, 400, 500),
    "BackpackCrafting": ("no", "yes", "limited", "workbench only"),
    "DeathPenalty": ("none", "xp only", "injured", "permanent death"),
    "DropOnDeath": ("none", "all", "toolbelt only", "backpack only", "equipment", "carried only", "delete all"),
    "DropOnQuit": ("none", "all", "toolbelt only", "backpack only", "equipment", "carried only"),
    "LoseItemsOnDeathType": ("none", "all", "toolbelt only", "backpack only", "equipment", "carried only"),
    "DegradeItemsOnDeath": ("none", "durability", "max durability", "both"),
    "TraderHourPresets": ("default", "morning", "mid day", "evening", "night", "bm closed", "always open"),
    "YesNo": ("no", "yes"),
    "Celebrate": ("no", "yes", "headshot only"),
    "ShowXP": ("all", "bar only", "notifications only", "none"),
    "HeadshotMode": ("none", "headshot only", "headshot finisher"),
    "MaxEnemyType": ("normals", "strongs", "specials", "ferals", "radiated", "elites"),
    "MaxTechType": ("none", "tech 0", "tech 1", "tech 2", "tech 3"),
    "LoseItemCount": ("1-3", "1-5", "1-10", "1-20", "3-5", "5-7", "5-10", "7-10", "10-15", "15-20"),
    "DayNightLength": ("10", "20", "30", "40", "50", "60", "90", "120"),
    "DayLightLength": ("always night", "4", "6", "8", "10", "12", "14", "16", "18", "20", "always day"),
    "LootRespawnDays": ("disabled", "5", "7", "10", "15", "20", "30", "40", "50"),
    "Gravity": percent(50, 60, 70, 80, 90, 100),
    "SlowToFast": ("default", "very slow", "slow", "normal", "fast", "very fast"),
    "BiomeEnemyDensity": ("none", "default", "very low", "low", "medium", "high", "very high"),
    "SmeltingType": ("smelter", "recipes"),
    "RepairTypes": ("none", "repair only", "combine only", "both"),
    "MaxDegradationAmounts": percent(0, 5, 10, 15, 20, 25),
    "CropGrowthSpeed": ("none", "instant") + percent(20, 50, 75, 100, 150, 200, 300),
    "ZombieFeralSense": ("disabled", "day", "night", "all"),
    "FullChickenStressEvent": ("none", "random", "chicken drop", "angry chicken", "zombie horde", "murder chickens"),
    "ShowLocationTypes": ("no", "yes", "name only"),
    "MaxStackSize": percent(25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 400, 500),
}

# Each option: its number in a code, its values, and its default. In the order of the
# game's Sandbox Options screen. Taken from SandboxOptionManager.SetupOptions in the game.
SANDBOX_OPTIONS = {
    "RangedDamage": (0, "DamageValues", "100%"),
    "MeleeDamage": (1, "DamageValues", "100%"),
    "BlockDamage": (2, "DamageValues", "100%"),
    "TerrainDamage": (3, "DamageValues", "100%"),
    "HeadshotMultiplier": (4, "DamageValues", "100%"),
    "IncomingDamage": (17, "DamageValues", "100%"),
    "WalkSpeed": (6, "PlayerSpeedValuesWithNone", "100%"),
    "RunSpeed": (7, "PlayerSpeedValues", "100%"),
    "CrouchSpeed": (5, "PlayerSpeedValues", "100%"),
    "CrouchRunSpeed": (112, "PlayerSpeedValues", "100%"),
    "JumpStrength": (8, "JumpStrength", "100%"),
    "StaminaRegen": (10, "StaminaRegen", "100%"),
    "StaminaUsage": (9, "StaminaUsage", "100%"),
    "XPMultiplier": (18, "XPGain", "100%"),
    "ShowXP": (19, "ShowXP", "all"),
    "PlayerLevelBonusApplied": (11, "YesNo", "yes"),
    "SkillGainRate": (116, "SkillGainRate", "1"),
    "SkillPointsPerLevel": (117, "PointsPer", "1"),
    "NewbieCoat": (15, "YesNo", "yes"),
    "DeathPenalty": (26, "DeathPenalty", "xp only"),
    "LoseItemsOnDeathType": (22, "LoseItemsOnDeathType", "none"),
    "LoseItemsOnDeathCount": (23, "LoseItemCount", "1-3"),
    "DegradeItemsOnDeath": (24, "DegradeItemsOnDeath", "none"),
    "DegradeAmountOnDeath": (25, "MaxDegradationAmounts", "10%"),
    "DropOnDeath": (27, "DropOnDeath", "all"),
    "DropOnQuit": (28, "DropOnQuit", "none"),
    "HungerMultiplier": (161, "StaminaUsage", "100%"),
    "ThirstMultiplier": (162, "StaminaUsage", "100%"),
    "InfectionChance": (160, "SpeedValues", "100%"),
    "InfectionRate": (29, "SpeedValues", "100%"),
    "StackSizeMultiplier": (163, "MaxStackSize", "100%"),
    "EncumbranceModifier": (20, "Encumbrance", "default"),
    "JarRefund": (12, "JarRefund", "60%"),
    "EnemySpawnMode": (30, "YesNo", "yes"),
    "MaxEnemyTier": (43, "MaxEnemyType", "elites"),
    "BiomeDayEnemyDensity": (46, "BiomeEnemyDensity", "default"),
    "BiomeDayZombieRespawn": (44, "SlowToFast", "default"),
    "BiomeDayAnimalDensity": (155, "BiomeEnemyDensity", "default"),
    "BiomeDayAnimalRespawn": (45, "SlowToFast", "default"),
    "BiomeNightEnemyDensity": (158, "BiomeEnemyDensity", "default"),
    "BiomeNightZombieRespawn": (156, "SlowToFast", "default"),
    "BiomeNightAnimalDensity": (159, "BiomeEnemyDensity", "default"),
    "BiomeNightAnimalRespawn": (157, "SlowToFast", "default"),
    "EntityDamage": (31, "DamageValues", "100%"),
    "EntityIncomingDamage": (42, "DamageValuesNoNone", "100%"),
    "BlockDamageAI": (32, "DamageValues", "100%"),
    "BlockDamageAIBM": (33, "DamageValues", "100%"),
    "HeadshotMode": (16, "HeadshotMode", "none"),
    "ShowHealthBars": (13, "YesNo", "no"),
    "ShowEnemyDamage": (14, "YesNo", "no"),
    "ZombieMove": (34, "ZombieSpeeds", "walk"),
    "ZombieMoveNight": (35, "ZombieSpeeds", "sprint"),
    "ZombieFeralMove": (36, "ZombieSpeeds", "sprint"),
    "ZombieBMMove": (37, "ZombieSpeeds", "sprint"),
    "ZombieFeralSense": (38, "ZombieFeralSense", "disabled"),
    "AISmellMode": (39, "AISmellMode", "run"),
    "ZombieRageChance": (41, "ZombieRageChance", "15%"),
    "AllowZombieDigging": (40, "YesNo", "yes"),
    "ZombiesEatAnimals": (47, "YesNo", "yes"),
    "GlobalGSModifier": (60, "LowDefaultHigh", "default"),
    "BiomeGSModifier": (61, "LowDefaultHigh", "default"),
    "BiomeProgression": (55, "YesNo", "yes"),
    "TemperatureSurvival": (56, "YesNo", "yes"),
    "MaxTechType": (74, "MaxTechType", "tech 3"),
    "WorkstationsInTheWild": (73, "JarRefund", "0%"),
    "BloodMoonFrequency": (48, "BloodMoonFrequency", "7"),
    "BloodMoonRange": (49, "BloodMoonRange", "0"),
    "BloodMoonEnemyCount": (51, "BloodMoonCount", "8"),
    "BloodMoonWarning": (50, "BloodMoonWarning", "morning"),
    "AirDropFrequency": (52, "AirDrops", "3"),
    "AirDropRandomTime": (54, "AirDropRandomTime", "none"),
    "StormFreq": (57, "StormFrequency", "100%"),
    "StormWarning": (58, "YesNo", "yes"),
    "HeatMapSensitivity": (59, "DisabledLowDefaultHigh", "default"),
    "DayNightLength": (66, "DayNightLength", "60"),
    "DayLightLength": (67, "DayLightLength", "18"),
    "AirDropMarker": (53, "YesNo", "yes"),
    "AllowMap": (68, "YesNo", "yes"),
    "AllowCompass": (69, "YesNo", "yes"),
    "AllowScreenMarkers": (70, "YesNo", "yes"),
    "ShowLocationInfo": (71, "ShowLocationTypes", "yes"),
    "ShowDayTime": (72, "YesNo", "yes"),
    "LootMaxTier": (77, "ItemTierOptions", "default"),
    "GlobalLSModifier": (62, "LowDefaultHigh", "default"),
    "BiomeLSModifier": (63, "LowDefaultHigh", "default"),
    "POITierLSModifier": (64, "LowDefaultHigh", "default"),
    "LootRespawnDays": (75, "LootRespawnDays", "7"),
    "LootTimer": (76, "SpeedValues", "100%"),
    "LootBagChance": (90, "LootAbundanceValues", "100%"),
    "GlobalLootCount": (78, "LootAbundanceValues", "100%"),
    "FoodLootCount": (79, "LootAbundanceValues", "100%"),
    "DrinkLootCount": (80, "LootAbundanceValues", "100%"),
    "MedicalLootCount": (81, "LootAbundanceValues", "100%"),
    "AmmoLootCount": (82, "LootAbundanceValues", "100%"),
    "ResourceLootCount": (83, "LootAbundanceValues", "100%"),
    "ArmorLootCount": (84, "LootAbundanceValues", "100%"),
    "MeleeLootCount": (85, "LootAbundanceValues", "100%"),
    "RangedLootCount": (86, "LootAbundanceValues", "100%"),
    "DukesLootCount": (87, "LootAbundanceValues", "100%"),
    "CraftingMagazinesLootCount": (88, "LootAbundanceValues", "100%"),
    "BookLootCount": (111, "LootAbundanceValues", "100%"),
    "TreasureMapChance": (89, "PlayerSpeedValues", "100%"),
    "MiningOutput": (101, "LootAbundanceValues", "100%"),
    "CropOutput": (91, "LootAbundanceValues", "100%"),
    "SeedDropOutput": (92, "LootAbundanceValues", "100%"),
    "HarvestingOutput": (102, "LootAbundanceValues", "100%"),
    "CropGrowthSpeed": (93, "CropGrowthSpeed", "100%"),
    "CraftingProgression": (96, "YesNo", "yes"),
    "CraftingMaxTier": (100, "ItemTierOptions", "default"),
    "PointsPerMagazine": (115, "PointsPer", "1"),
    "BackpackCrafting": (94, "BackpackCrafting", "yes"),
    "WorkstationCrafting": (95, "YesNo", "yes"),
    "SmeltingType": (104, "SmeltingType", "smelter"),
    "CraftingTime": (97, "SpeedValues", "100%"),
    "CraftingInput": (98, "SpeedValues", "100%"),
    "CraftingOutput": (99, "StaminaRegen", "100%"),
    "ScrappingOutput": (103, "SpeedValues", "100%"),
    "DewCollectorTime": (105, "SpeedValues", "100%"),
    "DewCollectorOutput": (106, "CollectorOutput", "100%"),
    "DewCollectorInput": (107, "DewCollectorInput", "100%"),
    "ApiaryTime": (108, "SpeedValues", "100%"),
    "ApiaryOutput": (109, "CollectorOutput", "100%"),
    "ApiaryInput": (110, "ApiaryInput", "100%"),
    "ChickenCoopTime": (152, "SpeedValues", "100%"),
    "ChickenCoopOutput": (153, "CollectorOutput", "100%"),
    "ChickenCoopInput": (154, "ApiaryInput", "100%"),
    "FullChickenStressEvent": (164, "FullChickenStressEvent", "random"),
    "ItemDegradation": (21, "DisabledLowDefaultHigh", "default"),
    "RepairTypes": (113, "RepairTypes", "both"),
    "MaxDegradationAmount": (114, "MaxDegradationAmounts", "0%"),
    "TradersEnabled": (128, "YesNo", "yes"),
    "VendingEnabled": (129, "YesNo", "yes"),
    "TraderHours": (127, "TraderHourPresets", "default"),
    "TraderProtection": (132, "TraderArea", "yes"),
    "TraderDialog": (126, "YesNo", "yes"),
    "GlobalTSModifier": (65, "LowDefaultHigh", "default"),
    "TraderMaxTier": (136, "ItemTierOptions", "default"),
    "TraderItemAbundance": (134, "LowDefaultHigh", "default"),
    "VendingItemAbundance": (138, "LowDefaultHigh", "default"),
    "TraderResetInterval": (133, "TraderResetInterval", "default"),
    "VendingResetInterval": (137, "TraderResetInterval", "default"),
    "TraderSellPrices": (130, "BarterValues", "100%"),
    "TraderBuyPrices": (131, "BarterValues", "100%"),
    "TraderBuyLimit": (135, "StarterSkillPoints", "3"),
    "ChallengesEnabled": (139, "YesNo", "yes"),
    "QuestsEnabled": (118, "YesNo", "yes"),
    "IntroChallengesEnabled": (140, "YesNo", "yes"),
    "IntroQuestEnabled": (119, "YesNo", "yes"),
    "TraderToTraderQuestsEnabled": (120, "YesNo", "yes"),
    "BuriedQuestsEnabled": (124, "YesNo", "yes"),
    "POIQuestsEnabled": (125, "YesNo", "yes"),
    "QuestsPerTier": (122, "QuestPerTier", "10"),
    "QuestProgressionDailyLimit": (123, "QuestPerDay", "4"),
    "StarterSkillPoints": (121, "StarterSkillPoints", "4"),
    "VehicleFuelUsage": (141, "DamageValues", "100%"),
    "VehicleEntityDamage": (142, "DamageValues", "100%"),
    "VehicleBlockDamage": (143, "DamageValues", "100%"),
    "VehicleSelfDamage": (144, "DamageValues", "100%"),
    "ElectricalOutput": (145, "StaminaRegen", "100%"),
    "SillyCelebrate": (146, "Celebrate", "no"),
    "SillyBigHeads": (147, "YesNo", "no"),
    "SillyTinyZombies": (148, "YesNo", "no"),
    "SillyLowGravity": (150, "Gravity", "100%"),
    "SillySounds": (149, "YesNo", "no"),
    "SillyBlackandWhite": (151, "YesNo", "no"),
}


def sandbox_path(config_dir=CONFIG_DIR):
    return os.path.join(config_dir, SANDBOX_FILE)


def read_sandbox_options(path):
    """The values in sandbox.xml, by option name, spelled as in SANDBOX_VALUES.

    Stops if a value is not one the game offers, since the code could not hold it.
    """
    properties = read_properties(parse_xml(path), path, "SandboxSettings")
    chosen = {}
    for name, value in properties.items():
        if name not in SANDBOX_OPTIONS:
            log(f"WARNING: {path}: the game has no sandbox option {name}. Check the spelling.")
            continue
        values = SANDBOX_VALUES[SANDBOX_OPTIONS[name][1]]
        wanted = " ".join(value.lower().split())
        match = [allowed for allowed in values if wanted in (allowed, allowed.rstrip("%"))]
        if not match:
            fail(f"{path}: {name} cannot be {value!r}. The game offers: {', '.join(values)}")
        chosen[name] = match[0]
    return chosen


def sandbox_code(chosen):
    """The game's code for these options: the version letter, then for each option
    that is not at its default two letters for its number and one for its value."""
    parts = [SANDBOX_CODE_VERSION]
    for name, value in sorted(chosen.items(), key=lambda item: SANDBOX_OPTIONS[item[0]][0]):
        number, value_set, default = SANDBOX_OPTIONS[name]
        if value != default:
            index = SANDBOX_VALUES[value_set].index(value)
            parts.append(chr(65 + number // 26) + chr(65 + number % 26) + chr(65 + index))
    return "".join(parts)


def decode_sandbox_code(code):
    """Every option's value for a code. Options the code does not list are at their default."""
    code = code.strip().upper()
    if not re.fullmatch(f"{SANDBOX_CODE_VERSION}([A-Z]{{3}})*", code):
        fail(f"{code!r} is not a sandbox code. A code starts with {SANDBOX_CODE_VERSION!r}, "
             "then has 3 letters per option, for example AAAJABJACJADJARFBNC.")
    names = {number: name for name, (number, _, _) in SANDBOX_OPTIONS.items()}
    values = {name: default for name, (_, _, default) in SANDBOX_OPTIONS.items()}
    for start in range(1, len(code), 3):
        number = (ord(code[start]) - 65) * 26 + ord(code[start + 1]) - 65
        index = ord(code[start + 2]) - 65
        name = names.get(number)
        if name is None or index >= len(SANDBOX_VALUES[SANDBOX_OPTIONS[name][1]]):
            log(f"WARNING: skipped {code[start:start + 3]} in the code: this version of "
                "sdtd does not know that option or value.")
            continue
        values[name] = SANDBOX_VALUES[SANDBOX_OPTIONS[name][1]][index]
    return values


def write_sandbox_file(path, values):
    """Put the values into sandbox.xml, keeping its layout and comments."""
    text = '<?xml version="1.0"?>\n<SandboxSettings>\n</SandboxSettings>\n'
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    comments = [match.span() for match in COMMENT_PATTERN.finditer(text)]
    placed = set()

    def fill(match):
        name = match.group(2)
        if name not in values or any(start <= match.start() < end for start, end in comments):
            return match.group(0)
        placed.add(name)
        return match.group(1) + quote_attribute(values[name]) + match.group(4)

    text = PROPERTY_PATTERN.sub(fill, text)
    missing = [name for name in values if name not in placed]
    end = text.rfind("</SandboxSettings>")
    if end < 0:
        fail(f"{path} has no </SandboxSettings>.")
    text = text[:end] + "".join(
        f'\t<property name="{name}" value="{quote_attribute(values[name])}"/>\n' for name in missing
    ) + text[end:]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def sandbox(args):
    path = sandbox_path()
    if not args:
        if not os.path.isfile(path):
            fail(f"{path} is missing. Restore it from git.")
        print(sandbox_code(read_sandbox_options(path)))
        return
    drop_privileges([HOME_DIR])
    values = decode_sandbox_code(args[0])
    try:
        write_sandbox_file(path, values)
    except PermissionError:
        fail(f"cannot write {path}. Run it with the pull service, where /config is writable: "
             "docker compose -f images/7dtd/docker-compose.yml run --rm pull sandbox <code>")
    changed = [name for name, value in values.items() if value != SANDBOX_OPTIONS[name][2]]
    for name in changed:
        log(f"{name} = {values[name]} (default {SANDBOX_OPTIONS[name][2]})")
    log(f"Wrote {path}: {len(changed)} option(s) differ from the game's defaults.")


# --- game files (Data/Config, platform.cfg, ...) -------------------------------


def count_elements(root):
    # element.tag is a callable for comments, so this skips them.
    return sum(1 for element in root.iter() if isinstance(element.tag, str))


def check_full_copy(path, original_path, rel):
    """Stop if the file cannot stand in for the game's, warn if it looks like a fragment."""
    root = parse_xml(path).getroot()
    game_root = parse_xml(original_path).getroot()
    if root.tag != game_root.tag:
        fail(f"{rel}: the root element must be <{game_root.tag}>, not <{root.tag}>.")
    count, game_count = count_elements(root), count_elements(game_root)
    if count * 2 < game_count:
        log(f"WARNING: {rel} has {count} elements, the game's own copy has {game_count}. "
            "Your file replaces the game's whole file, so whatever is missing from it is gone "
            'from the game. If it is an old fragment, delete it, run "sdtd pull" and make your '
            "changes in the full file.")


def apply_game_files(config_dir=CONFIG_DIR, server_dir=SERVER_DIR, data_dir=DATA_DIR, pulled=None):
    """Put your changed copies of game files in place of the game's own.

    While your copy is in place, the game's is kept in /data/.sdtd-originals, so
    undoing your change or deleting the file puts the game's copy back.
    """
    shipped = pulled_files(pulled)
    originals_dir = os.path.join(data_dir, ORIGINALS_SUBDIR)
    state_path = os.path.join(originals_dir, ORIGINALS_STATE_FILE)
    written = read_json(state_path, {})  # rel -> hash of what we put in the game
    legacy_state = os.path.join(originals_dir, LEGACY_STATE_FILE)
    if os.path.isfile(legacy_state):
        os.remove(legacy_state)

    yours = []
    for rel in changed_files(config_dir, pulled):
        if os.path.isfile(os.path.join(server_dir, rel)):
            yours.append(rel)
        else:
            log(f"WARNING: the game has no {rel}, so the repo's copy is ignored. "
                'Check the spelling, or run "sdtd pull".')
    stored = walk_files(originals_dir) if os.path.isdir(originals_dir) else []

    applied, restored = [], []
    for rel in sorted(set(yours) | set(stored)):
        target = os.path.join(server_dir, rel)
        original = os.path.join(originals_dir, rel)
        if not os.path.isfile(target):
            # A game update dropped the file, so there is nothing to restore.
            remove_file(originals_dir, rel)
            written.pop(rel, None)
            continue
        if not os.path.isfile(original) or (rel in written and content_hash(target) != written[rel]):
            # The first time, or a game update replaced our copy: keep the game's current file.
            copy_file(target, original)
        if rel in yours:
            source = os.path.join(config_dir, rel)
            if rel.endswith(".xml"):
                check_full_copy(source, original, rel)
            if rel in shipped and shipped[rel] != content_hash(original):
                log(f"WARNING: {rel}: the game changed this file since your last \"sdtd pull\", "
                    "so your copy is based on the old version. To move to the new one, delete "
                    'your copy, run "sdtd pull" and make your changes again (git diff shows them).')
            shutil.copyfile(source, target)
            written[rel] = content_hash(target)
            applied.append(rel)
        else:
            shutil.copyfile(original, target)
            remove_file(originals_dir, rel)
            written.pop(rel, None)
            restored.append(rel)

    if written or os.path.isdir(originals_dir):
        os.makedirs(originals_dir, exist_ok=True)
        write_json(state_path, written)
    for rel in applied:
        log(f"Applied your {rel} -> {os.path.join(server_dir, rel)}")
    for rel in restored:
        log(f"Restored the game's own {rel} (the repo's copy is unchanged or gone).")


def check_repo_config(config_dir=CONFIG_DIR):
    """Stop before the long game update if a repo config file is broken."""
    pulled = read_pulled_state(config_dir)
    config_file = os.path.join(config_dir, "serverconfig.xml")
    if os.path.isfile(config_file):
        read_properties(parse_xml(config_file), config_file)
    if os.path.isfile(sandbox_path(config_dir)):
        read_sandbox_options(sandbox_path(config_dir))
    if admin_file_changed(config_dir, pulled):
        parse_xml(os.path.join(config_dir, "serveradmin.xml"))
    for rel in changed_files(config_dir, pulled):
        if rel.endswith(".xml"):
            parse_xml(os.path.join(config_dir, rel))


def apply_repo_config(config_dir=CONFIG_DIR, server_dir=SERVER_DIR, data_dir=DATA_DIR):
    pulled = read_pulled_state(config_dir)
    if pulled is None:
        log('configs/7dtd has no copies of the game\'s files yet. Run "sdtd pull" to get '
            "every file you can configure.")
    elif pulled.get("branch") != game_branch():
        log(f"WARNING: configs/7dtd was pulled from branch {pulled.get('branch')!r}, but the "
            f'server runs {game_branch()!r}. Run "sdtd pull" with SDTD_BRANCH={game_branch()}.')
    default_config = os.path.join(server_dir, "serverconfig.xml")
    if not os.path.isfile(default_config):
        fail(f"{default_config} is missing. Is the game installed? Set SDTD_UPDATE=true.")
    generated = {}
    if os.path.isfile(sandbox_path(config_dir)):
        chosen = read_sandbox_options(sandbox_path(config_dir))
        generated["SandboxCode"] = sandbox_code(chosen)
        changed = [name for name, value in chosen.items() if value != SANDBOX_OPTIONS[name][2]]
        log(f"Sandbox options from {sandbox_path(config_dir)}: {len(changed)} differ from the "
            f"game's defaults. SandboxCode={generated['SandboxCode']}")
    config_file = os.path.join(data_dir, "serverconfig.xml")
    properties = merge_server_config(
        default_config, os.path.join(config_dir, "serverconfig.xml"), config_file,
        (pulled or {}).get("serverconfig", {}), generated,
    )
    apply_admin_file(config_dir, data_dir, properties.get("AdminFileName", "serveradmin.xml"), pulled)
    sync_mods(os.path.join(config_dir, "Mods"), os.path.join(server_dir, "Mods"))
    apply_game_files(config_dir, server_dir, data_dir, pulled)
    return config_file, properties


# --- sdtd pull --------------------------------------------------------------


def download_config_files(runner, branch, target_dir):
    """Download only the game's config files. Returns the manifest id and date."""
    shutil.rmtree(target_dir, ignore_errors=True)
    os.makedirs(target_dir)
    file_list = os.path.join(HOME_DIR, "pull-files.txt")
    with open(file_list, "w") as handle:
        handle.write("\n".join(PULL_FILE_LIST) + "\n")
    log(f"Downloading the game's config files (branch {branch}).")
    lines = []
    code = runner.run(
        [DEPOT_DOWNLOADER, "-app", APP_ID, "-depot", LINUX_DEPOT_ID, "-branch", branch,
         "-filelist", file_list, "-dir", target_dir],
        output_filter=lambda stream: print_download_progress(stream, lines),
    )
    if runner.stopping:
        sys.exit(0)
    if code != 0:
        fail(f"DepotDownloader failed with exit code {code}")
    for line in lines:
        match = re.search(r"Manifest (\d+) \(([^)]*)\)", line)
        if match:
            return match.group(1), match.group(2)
    return None, None


def pull():
    drop_privileges([HOME_DIR])
    hint = ("Set PUID and PGID to the owner of configs/7dtd (id -u, id -g). With rootless "
            "Podman use PUID=0 and PGID=0: root in the container is your own user there. "
            "Run pull with its own service, where /config is writable: "
            "docker compose -f images/7dtd/docker-compose.yml run --rm pull")
    if not os.access(CONFIG_DIR, os.W_OK):
        fail(f"cannot write to {CONFIG_DIR}. {hint}")
    pulled = read_pulled_state(CONFIG_DIR)
    config_path = os.path.join(CONFIG_DIR, "serverconfig.xml")
    values = {}
    if os.path.isfile(config_path):
        values = read_properties(parse_xml(config_path), config_path)

    branch = game_branch()
    staging = os.path.join(HOME_DIR, "pull")
    manifest, manifest_date = download_config_files(Runner(), branch, staging)
    shipped = {rel: os.path.join(staging, rel) for rel in walk_files(staging)}
    game_config = shipped.pop("serverconfig.xml", None)
    if game_config is None:
        fail(f"The download has no serverconfig.xml. Check SDTD_BRANCH={branch}.")
    shipped["serveradmin.xml"] = ADMIN_TEMPLATE

    old_files = pulled_files(pulled)
    files = {}
    added, updated, kept, removed = [], [], [], []
    try:
        defaults, changed_settings = write_full_server_config(
            game_config, values, (pulled or {}).get("serverconfig", {}), config_path)
        for rel in sorted(shipped):
            source, target = shipped[rel], os.path.join(CONFIG_DIR, rel)
            new_hash, old_hash = content_hash(source), old_files.get(rel)
            if not os.path.isfile(target):
                copy_file(source, target)
                added.append(rel)
            elif content_hash(target) == new_hash:
                pass
            elif content_hash(target) == old_hash:
                copy_file(source, target)
                updated.append(rel)
            else:
                # You changed it. Remember what the game shipped when you did,
                # so it keeps counting as changed.
                kept.append(rel)
                if old_hash:
                    files[rel] = old_hash
                    if old_hash != new_hash:
                        log(f"WARNING: kept your {rel}, but the game changed it too. To move to "
                            'the game\'s new version, delete your copy, run "sdtd pull" again '
                            "and make your changes again (git diff shows them).")
                else:
                    log(f"NOTE: kept your {rel}: it differs from the game's copy. If it is an old "
                        'fragment with only your changes, delete it and run "sdtd pull" again '
                        "to get the full file.")
                continue
            files[rel] = new_hash

        for rel in sorted(set(old_files) - set(shipped)):
            target = os.path.join(CONFIG_DIR, rel)
            if not os.path.isfile(target):
                continue
            if content_hash(target) == old_files[rel]:
                remove_file(CONFIG_DIR, rel)
                removed.append(rel)
            else:
                files[rel] = old_files[rel]
                log(f"WARNING: the game no longer has {rel}. Kept your changed copy, but the "
                    "server ignores it.")

        write_json(os.path.join(CONFIG_DIR, PULLED_STATE_FILE), {
            "branch": branch,
            "manifest": manifest,
            "manifest_date": manifest_date,
            "serverconfig": defaults,
            "files": dict(sorted(files.items())),
        })
    except PermissionError as error:
        fail(f"cannot write {error.filename}. {hint}")
    shutil.rmtree(staging, ignore_errors=True)

    for label, names in (("new", added), ("updated", updated), ("kept, you changed it", kept),
                         ("removed, the game dropped it", removed)):
        if len(names) > 10 and label == "new":
            log(f"{len(names)} new files, for example {', '.join(names[:3])}")
            continue
        for rel in names:
            log(f"{label}: {rel}")
    log(f"serverconfig.xml: the game's full file, with {changed_settings} setting(s) that differ "
        "from its defaults.")
    log(f"Pulled game build {manifest} ({manifest_date}) from branch {branch}: {len(added)} new, "
        f"{len(updated)} updated, {len(kept)} kept, {len(removed)} removed.")


# --- telnet -----------------------------------------------------------------


class Telnet:
    """Minimal client for the 7 Days to Die telnet console."""

    READY = "Press 'help' to get a list of all commands"

    def __init__(self, port, password, timeout=10):
        host = "127.0.0.1"
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buffer = ""
        text = self.read_until([self.READY, "Please enter password:"], timeout)
        if "Please enter password:" in text:
            self.send(password)
            self.read_until([self.READY], timeout)

    def read_until(self, patterns, timeout):
        deadline = time.monotonic() + timeout
        while not any(pattern in self.buffer for pattern in patterns):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no {patterns[0]!r} from the telnet console")
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("the telnet console closed the connection")
            self.buffer += chunk.decode("utf-8", errors="replace")
        text, self.buffer = self.buffer, ""
        return text

    def read_for(self, seconds):
        deadline = time.monotonic() + seconds
        output = self.buffer
        self.buffer = ""
        while time.monotonic() < deadline:
            self.sock.settimeout(max(deadline - time.monotonic(), 0.01))
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            output += chunk.decode("utf-8", errors="replace")
        return output

    def send(self, line):
        self.sock.sendall(line.encode("utf-8") + b"\n")

    def close(self):
        try:
            self.send("exit")
        except OSError:
            pass
        self.sock.close()


def telnet_settings():
    properties = {}
    config_file = os.path.join(DATA_DIR, "serverconfig.xml")
    if os.path.isfile(config_file):
        properties = read_properties(parse_xml(config_file), config_file)
    return int(properties.get("TelnetPort", "8081")), properties.get("TelnetPassword", "")


def command(args):
    if not args:
        fail('usage: sdtd cmd "<console command>"')
    port, password = telnet_settings()
    try:
        console = Telnet(port, password)
    except (OSError, TimeoutError) as error:
        fail(f"cannot reach the server console on port {port}: {error}")
    console.send(" ".join(args))
    print(console.read_for(3).strip())
    console.close()


# --- install and run --------------------------------------------------------


def check_cpu():
    """Stop before the 14 GB download if x86_64 is only emulated (for example on Apple Silicon).

    The game's Mono runtime aborts under Rosetta and QEMU:
    "Assertion at ../../mono/arch/amd64/../x86/x86-codegen.h:410".
    """
    if env_flag("SDTD_ALLOW_EMULATION", "false"):
        return
    try:
        with open("/proc/cpuinfo") as cpuinfo_file:
            cpuinfo = cpuinfo_file.read()
    except OSError:
        return
    if "VirtualApple" in cpuinfo or "CPU implementer" in cpuinfo:
        fail("This host runs x86_64 programs with emulation (for example Apple Silicon or another ARM CPU). "
             "The 7 Days to Die server crashes in emulation. Run this service on an x86_64 host. "
             "To try anyway, set SDTD_ALLOW_EMULATION=true.")


def drop_privileges(paths):
    """Run as PUID:PGID so files in the bind mounts belong to the host user."""
    if os.getuid() != 0:
        return
    uid = int(os.environ.get("PUID", "1000"))
    gid = int(os.environ.get("PGID", "1000"))
    if uid == 0:
        return
    for path in paths:
        os.makedirs(path, exist_ok=True)
        stat = os.stat(path)
        if (stat.st_uid, stat.st_gid) != (uid, gid):
            subprocess.run(["chown", "-R", f"{uid}:{gid}", path], check=True)
    os.setgroups([])
    os.setgid(gid)
    os.setuid(uid)
    log(f"Running as uid {uid}, gid {gid}")


class Runner:
    """Start child processes and stop them cleanly on SIGTERM or SIGINT."""

    def __init__(self):
        self.child = None
        self.stopping = False
        self.kill_at = None
        self.telnet = None  # (port, password) once the game server is running
        signal.signal(signal.SIGTERM, self.on_signal)
        signal.signal(signal.SIGINT, self.on_signal)

    def on_signal(self, signum, frame):
        if self.stopping:
            return
        self.stopping = True
        log(f"Received {signal.Signals(signum).name}; stopping.")
        if self.child is None or self.child.poll() is not None:
            sys.exit(0)
        self.kill_at = time.monotonic() + STOP_TIMEOUT_SECONDS
        if self.telnet and self.shutdown_over_telnet():
            return
        self.child.terminate()

    def shutdown_over_telnet(self):
        port, password = self.telnet
        for _ in range(3):
            try:
                console = Telnet(port, password, timeout=5)
                console.send("shutdown")
                console.close()
                log("Sent 'shutdown' to the server. Waiting for it to save and exit.")
                return True
            except (OSError, TimeoutError) as error:
                log(f"Telnet shutdown failed ({error}); trying again.")
                time.sleep(2)
        return False

    def run(self, args, output_filter=None, **kwargs):
        if output_filter:
            kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        # A new session keeps a terminal Ctrl-C from reaching the child directly.
        self.child = subprocess.Popen(args, start_new_session=True, **kwargs)
        reader = None
        if output_filter:
            reader = threading.Thread(target=output_filter, args=(self.child.stdout,), daemon=True)
            reader.start()
        while True:
            try:
                code = self.child.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                if self.kill_at is not None and time.monotonic() > self.kill_at:
                    log("The process did not stop in time; killing it.")
                    self.child.kill()
                    self.kill_at = None
        if reader:
            reader.join(timeout=5)
        return code


def print_download_progress(stream, seen=None):
    """DepotDownloader prints two lines for each of about 17,000 files. Keep the log short.

    Every line also goes to seen, if given, for callers that need to read the output.
    """
    last_progress = 0.0
    for line in stream:
        line = line.rstrip()
        if seen is not None:
            seen.append(line)
        if line.startswith("Pre-allocating"):
            continue
        match = re.match(r"\s*(\d+\.\d+)% ", line)
        if match:
            if time.monotonic() - last_progress < 30:
                continue
            last_progress = time.monotonic()
            line = f"Download progress: {match.group(1)}%"
        print(line, flush=True)


def install_game(runner):
    branch = game_branch()
    installed = os.path.isfile(os.path.join(SERVER_DIR, SERVER_BINARY))
    if installed and not env_flag("SDTD_UPDATE", "true"):
        log("SDTD_UPDATE=false; skipping the update check.")
        return
    if installed:
        log(f"Checking for game updates (branch {branch}).")
    else:
        log(f"Installing the game (branch {branch}). This downloads about 14 GB.")
    args = [DEPOT_DOWNLOADER, "-app", APP_ID, "-depot", LINUX_DEPOT_ID,
            "-branch", branch, "-dir", SERVER_DIR]
    if env_flag("SDTD_VALIDATE", "false"):
        args.append("-validate")
    code = runner.run(args, output_filter=print_download_progress)
    if runner.stopping:
        sys.exit(0)
    if code != 0:
        fail(f"DepotDownloader failed with exit code {code}")
    os.chmod(os.path.join(SERVER_DIR, SERVER_BINARY), 0o755)


def run():
    check_cpu()
    drop_privileges([SERVER_DIR, DATA_DIR, HOME_DIR])
    check_repo_config()
    runner = Runner()
    install_game(runner)
    config_file, properties = apply_repo_config()
    runner.telnet = (int(properties.get("TelnetPort", "8081")), properties.get("TelnetPassword", ""))
    log(f"Starting the server. Game port {properties.get('ServerPort')}.")
    code = runner.run(
        [f"./{SERVER_BINARY}", "-logfile", "-", "-quit", "-batchmode", "-nographics",
         "-dedicated", f"-configfile={config_file}"],
        cwd=SERVER_DIR,
        env={**os.environ, "LD_LIBRARY_PATH": "."},
    )
    log(f"The server exited with code {code}.")
    sys.exit(0 if runner.stopping else code)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "pull", "cmd", "sandbox"):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "pull":
        pull()
    elif sys.argv[1] == "sandbox":
        sandbox(sys.argv[2:])
    else:
        command(sys.argv[2:])


if __name__ == "__main__":
    main()
