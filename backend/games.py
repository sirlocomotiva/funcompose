"""Game registry — single source of truth for every supported game.

Each entry defines:
  - public metadata served by GET /api/games
  - the Docker image + ports + volumes used to create containers
  - a build_env() that turns a flat config dict into container env vars
  - declarative `fields` driving the frontend's dynamic forms

Adding a new game = adding one entry here. Nothing else changes.
"""

import os


def _field(key, label, type="text", default=None, required=False, options=None,
           help=None, placeholder=None, show_if=None):
    return {
        "key": key,
        "label": label,
        "type": type,
        "default": default,
        "required": required,
        "options": options,
        "help": help,
        "placeholder": placeholder,
        "show_if": show_if,
    }


def _mem_options(*values):
    return [{"value": str(v), "label": f"{v} GB"} for v in values]


def _cf_slug(value):
    """Accept a CurseForge slug or full page URL; return the slug."""
    if not value:
        return ""
    v = str(value).strip()
    if "/modpacks/" in v:
        v = v.split("/modpacks/")[-1]
    v = v.split("/")[0].split("?")[0].strip("/")
    return v


def _env_minecraft(config):
    server_type = config.get("server_type", "PAPER")
    online_mode = "TRUE" if config.get("online_mode", True) else "FALSE"
    env = {
        "EULA": "TRUE",
        "TYPE": server_type,
        "VERSION": str(config.get("version", "LATEST")),
        "MEMORY": f"{int(config.get('memory_gb', 4))}G",
        "MAX_PLAYERS": str(int(config.get("max_players", 20))),
        "MOTD": str(config.get("motd", "A Minecraft Server")),
        "DIFFICULTY": str(config.get("difficulty", "normal")).upper(),
        "ONLINE_MODE": online_mode,
    }

    if server_type == "AUTO_CURSEFORGE":
        slug = _cf_slug(config.get("cf_slug", ""))
        if slug:
            env["CF_SLUG"] = slug
        api_key = config.get("cf_api_key") or os.getenv("CF_API_KEY")
        if api_key:
            env["CF_API_KEY"] = api_key
        matcher = config.get("cf_filename_matcher")
        if matcher:
            env["CF_FILENAME_MATCHER"] = str(matcher)

    if server_type == "MODRINTH":
        modpack = config.get("modrinth_modpack", "")
        if modpack:
            env["MODRINTH_MODPACK"] = modpack

    projects = config.get("modrinth_projects", "")
    if projects:
        env["MODRINTH_PROJECTS"] = projects.replace("\n", ",")
        env["MODRINTH_ALLOWED_VERSION_TYPE"] = "release"

    pack_url = config.get("generic_pack_url", "")
    if pack_url:
        env["GENERIC_PACKS"] = pack_url

    extra_mods = config.get("extra_mods", "")
    if extra_mods:
        env["MODS"] = extra_mods.replace("\n", ",")

    return env


def _env_valheim(config):
    env = {
        "SERVER_NAME": str(config.get("server_name", "My Valheim Server")),
        "WORLD_NAME": str(config.get("world_name", "Dedicated")),
        "SERVER_PASS": str(config.get("password", "")),
        "SERVER_PUBLIC": "1" if config.get("public", False) else "0",
    }
    return {k: v for k, v in env.items() if v != ""}


_TERRARIA_DIFFICULTY = {"normal": 0, "expert": 1, "journey": 2, "master": 3}
_TERRARIA_SIZE = {"small": 1, "medium": 2, "large": 3}


def _env_terraria(config):
    world_name = str(config.get("world_name", "World"))
    env = {
        "autocreate": str(_TERRARIA_SIZE.get(config.get("world_size", "medium"), 2)),
        "worldname": world_name,
        "world": f"/world/{world_name}.wld",
        "maxplayers": str(int(config.get("max_players", 16))),
        "difficulty": str(_TERRARIA_DIFFICULTY.get(config.get("difficulty", "normal"), 0)),
    }
    if config.get("password"):
        env["pass"] = str(config["password"])
    if config.get("motd"):
        env["motd"] = str(config["motd"])
    if config.get("seed"):
        env["seed"] = str(config["seed"])
    return env


_DT2_WORLDS = {"Navezgane": "Navezgane", "Pregen04x10k": "Pregen04x10k", "NewRandom": "RWG"}


def _env_7dtd(config):
    env = {
        "START_MODE": "1",
        "VERSION": "stable",
        "SERVER_NAME": str(config.get("server_name", "My 7DtD Server")),
        "GAME_NAME": str(config.get("game_name", "game1")),
        "GAME_WORLD": _DT2_WORLDS.get(config.get("game_world", "Navezgane"), "Navezgane"),
        "SERVER_MAX_PLAYER_COUNT": str(int(config.get("max_players", 8))),
    }
    if config.get("server_password"):
        env["SERVER_PASSWORD"] = str(config["server_password"])
    return env


_MC_TYPES = [
    {"id": "VANILLA", "name": "Vanilla", "description": "Official Mojang server, no mods"},
    {"id": "PAPER", "name": "Paper", "description": "High-performance plugins server (recommended)"},
    {"id": "FABRIC", "name": "Fabric", "description": "Lightweight mod loader"},
    {"id": "FORGE", "name": "Forge", "description": "Classic mod loader"},
    {"id": "AUTO_CURSEFORGE", "name": "CurseForge Modpack", "description": "Install any CurseForge modpack"},
    {"id": "MODRINTH", "name": "Modrinth Modpack", "description": "Install any Modrinth .mrpack modpack"},
]


GAMES = {
    "minecraft": {
        "id": "minecraft",
        "name": "Minecraft",
        "tagline": "Vanilla, Paper, Fabric, Forge & any modpack",
        "icon": "\u26cf\ufe0f",
        "color": "#22c55e",
        "available": True,
        "coming_soon_note": None,
        "image": "itzg/minecraft-server:java21",
        "default_port": 25565,
        "port_protocol": "tcp",
        "extra_ports": [],
        "min_memory_gb": 1,
        "recommended_memory_gb": 4,
        "server_types": _MC_TYPES,
        "volumes": ["/data"],
        "build_env": _env_minecraft,
        "fields": [
            # Not rendered as a dropdown by the frontend (uses server_types pills);
            # declared here so validate_config coerces + preserves the value.
            _field("server_type", "Server Type", type="select", default="PAPER",
                   options=[{"value": t["id"], "label": t["name"]} for t in _MC_TYPES]),
            _field("memory_gb", "Memory", type="select", default=4, options=_mem_options(2, 4, 6, 8, 12, 16),
                   help="How much RAM the server gets"),
            _field("version", "Version", default="LATEST", placeholder="e.g. 1.21.1"),
            _field("max_players", "Max Players", type="number", default=20),
            _field("motd", "MOTD", default="A Minecraft Server",
                   help="Message shown in the multiplayer server list"),
            _field("difficulty", "Difficulty", type="select", default="normal",
                   options=[{"value": v, "label": v.capitalize()} for v in ("peaceful", "easy", "normal", "hard")]),
            _field("online_mode", "Online Mode", type="checkbox", default=True,
                   help="Require premium Microsoft accounts"),
            _field("cf_slug", "CurseForge Modpack", required=True,
                   show_if={"key": "server_type", "values": ["AUTO_CURSEFORGE"]},
                   placeholder="prominence-2-hasturian-era",
                   help="Modpack slug or full CurseForge page URL"),
            _field("cf_filename_matcher", "Modpack Version Filter", show_if={"key": "server_type", "values": ["AUTO_CURSEFORGE"]},
                   placeholder="4.0.1", help="Optional — pin a specific modpack release"),
            _field("cf_api_key", "CurseForge API Key", type="password",
                   show_if={"key": "server_type", "values": ["AUTO_CURSEFORGE"]},
                   help="Leave empty to use the CF_API_KEY configured in .env"),
            _field("modrinth_modpack", "Modrinth Modpack", required=True,
                   show_if={"key": "server_type", "values": ["MODRINTH"]},
                   placeholder="adrenaline", help="Modrinth slug or project URL (.mrpack)"),
            _field("modrinth_projects", "Extra Modrinth Mods", type="textarea",
                   help="Comma-separated Modrinth mod slugs, e.g. distanthorizons,xaeros-minimap"),
            _field("generic_pack_url", "Server Pack URL",
                   help="Direct URL to a .zip server pack installed on top of the server"),
            _field("extra_mods", "Extra Mods (.jar URLs)", type="textarea",
                   help="Comma-separated direct download URLs of .jar files"),
        ],
    },
    "valheim": {
        "id": "valheim",
        "name": "Valheim",
        "tagline": "Norse co-op survival for up to 10 vikings",
        "icon": "\U0001f6e1\ufe0f",
        "color": "#3b82f6",
        "available": True,
        "coming_soon_note": None,
        "image": "lloesche/valheim-server:latest",
        "default_port": 2456,
        "port_protocol": "udp",
        "extra_ports": [{"port": 2457, "protocol": "udp"}],
        "min_memory_gb": 2,
        "recommended_memory_gb": 4,
        "server_types": None,
        "volumes": ["/config", "/data"],
        "build_env": _env_valheim,
        "fields": [
            _field("memory_gb", "Memory", type="select", default=4, options=_mem_options(2, 4, 6, 8, 12, 16)),
            _field("server_name", "Server Name", default="My Valheim Server"),
            _field("world_name", "World Name", default="Dedicated"),
            _field("password", "Join Password", type="password", required=True,
                   help="Minimum 5 characters — players need it to join"),
            _field("public", "Public Server", type="checkbox", default=False,
                   help="List this server in the community browser"),
        ],
    },
    "terraria": {
        "id": "terraria",
        "name": "Terraria",
        "tagline": "2D sandbox adventure, dig fight explore",
        "icon": "\U0001f333",
        "color": "#f59e0b",
        "available": True,
        "coming_soon_note": None,
        "image": "ryshe/terraria:latest",
        "default_port": 7777,
        "port_protocol": "tcp",
        "extra_ports": [],
        "min_memory_gb": 1,
        "recommended_memory_gb": 2,
        "server_types": None,
        "volumes": ["/world"],
        "build_env": _env_terraria,
        "fields": [
            _field("memory_gb", "Memory", type="select", default=2, options=_mem_options(1, 2, 3, 4, 6, 8)),
            _field("world_name", "World Name", default="World"),
            _field("world_size", "World Size", type="select", default="medium",
                   options=[{"value": "small", "label": "Small"}, {"value": "medium", "label": "Medium"},
                            {"value": "large", "label": "Large"}]),
            _field("difficulty", "Difficulty", type="select", default="normal",
                   options=[{"value": v, "label": v.capitalize()} for v in ("normal", "expert", "master", "journey")]),
            _field("max_players", "Max Players", type="number", default=16),
            _field("password", "Server Password", help="Leave empty for no password"),
            _field("motd", "MOTD", help="Message shown to joining players"),
            _field("seed", "World Seed", help="Optional fixed seed for world generation"),
        ],
    },
    "7dtd": {
        "id": "7dtd",
        "name": "7 Days to Die",
        "tagline": "Open-world zombie survival — the horde comes every 7 days",
        "icon": "\U0001f9df",
        "color": "#ef4444",
        "available": True,
        "coming_soon_note": None,
        "image": "vinanrra/7dtd-server:latest",
        "default_port": 26900,
        "port_protocol": "tcp",
        "extra_ports": [
            {"port": 26900, "protocol": "udp"},
            {"port": 26901, "protocol": "udp"},
            {"port": 26902, "protocol": "udp"},
        ],
        "min_memory_gb": 6,
        "recommended_memory_gb": 8,
        "server_types": None,
        "volumes": ["/home/sdtdserver"],
        "build_env": _env_7dtd,
        "fields": [
            _field("memory_gb", "Memory", type="select", default=8, options=_mem_options(6, 8, 12, 16),
                   help="This game needs at least 6 GB"),
            _field("server_name", "Server Name", default="My 7DtD Server"),
            _field("game_name", "Save Game Slot", default="game1",
                   help="Name of the save-game folder"),
            _field("game_world", "World", type="select", default="Navezgane",
                   options=[{"value": "Navezgane", "label": "Navezgane (pre-generated)"},
                            {"value": "Pregen04x10k", "label": "Pre-generated 10k"},
                            {"value": "NewRandom", "label": "Random generated (slow first start)"}]),
            _field("server_password", "Server Password", type="password",
                   help="Leave empty for no password"),
            _field("max_players", "Max Players", type="number", default=8),
        ],
    },
    "hytale": {
        "id": "hytale",
        "name": "Hytale",
        "tagline": "Adventure & creativity — coming soon",
        "icon": "\U0001f3f0",
        "color": "#a855f7",
        "available": False,
        "coming_soon_note": "Hytale dedicated-server software isn't released yet. This slot activates automatically once it ships.",
        "image": None,
        "default_port": None,
        "port_protocol": "tcp",
        "extra_ports": [],
        "min_memory_gb": None,
        "recommended_memory_gb": None,
        "server_types": None,
        "volumes": [],
        "build_env": lambda cfg: {},
        "fields": [],
    },
}


# ---------------------------------------------------------------------------
# Config validation against field definitions
# ---------------------------------------------------------------------------

def get_game(game_id):
    game = GAMES.get(game_id)
    if not game or not game["available"]:
        return None
    return game


def _visible(field, config):
    cond = field.get("show_if")
    if not cond:
        return True
    current = config.get(cond["key"])
    return any(str(current) == str(v) for v in cond["values"])


class ConfigError(ValueError):
    pass


def validate_config(game_id, raw_config):
    """Coerce + validate a raw config dict against the game's FieldDefs.

    Returns a clean config containing only known keys, with defaults filled
    and hidden fields reset. Raises ConfigError on missing required values.
    """
    game = get_game(game_id)
    if not game:
        raise ConfigError(f"Unknown game '{game_id}'")

    raw = dict(raw_config or {})
    out = {}

    # server_type must resolve first so show_if conditions can see it.
    ordered = list(game["fields"])
    for i, f in enumerate(ordered):
        if f["key"] == "server_type":
            ordered.insert(0, ordered.pop(i))
            break

    for f in ordered:
        key = f["key"]
        visible = _visible(f, out)
        raw_value = raw.get(key)

        if not visible:
            out[key] = f["default"]
            continue

        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            if f.get("required"):
                raise ConfigError(f"'{f['label']}' is required")
            out[key] = f["default"]
            continue

        try:
            if f["type"] == "number":
                out[key] = int(raw_value)
            elif f["type"] == "checkbox":
                out[key] = bool(raw_value) if not isinstance(raw_value, str) else raw_value.lower() in ("true", "1", "yes")
            else:
                value = str(raw_value)
                opts = f.get("options") or []
                if opts and all(str(o["value"]).isdigit() for o in opts):
                    value = int(value)
                out[key] = value
        except (TypeError, ValueError):
            raise ConfigError(f"'{f['label']}' must be a number")

    return out


def public_def(game):
    """Serialize a registry entry for the API (drop internal keys)."""
    return {
        "id": game["id"],
        "name": game["name"],
        "tagline": game["tagline"],
        "icon": game["icon"],
        "color": game["color"],
        "available": game["available"],
        "coming_soon_note": game["coming_soon_note"],
        "default_port": game["default_port"],
        "port_protocol": game["port_protocol"],
        "extra_ports": game["extra_ports"],
        "min_memory_gb": game["min_memory_gb"],
        "recommended_memory_gb": game["recommended_memory_gb"],
        "server_types": game["server_types"],
        "fields": game["fields"],
    }


def list_public():
    return [public_def(g) for g in GAMES.values()]
