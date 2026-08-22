import json
import os
from typing import List, Optional

from config import SERVERS_FILE, DATA_PATH
from models.server import Server


def _ensure_data_dir():
    os.makedirs(DATA_PATH, exist_ok=True)


def _read() -> dict:
    _ensure_data_dir()
    if not os.path.exists(SERVERS_FILE):
        return {"servers": []}
    with open(SERVERS_FILE, "r") as f:
        data = json.load(f)
    data["servers"] = [_migrate(s) for s in data.get("servers", [])]
    return data


def _migrate(entry: dict) -> dict:
    """Convert pre-multi-game records (nested `minecraft` object) to the new shape."""
    if "minecraft" not in entry or "config" in entry:
        return entry

    mc = entry.pop("minecraft") or {}
    cfg = {
        "server_type": mc.get("type", "VANILLA"),
        "version": mc.get("version", "LATEST"),
        "max_players": mc.get("max_players", 20),
        "motd": mc.get("motd", "A Minecraft Server"),
        "online_mode": True,
    }

    memory = str(mc.get("memory", "")).upper().rstrip("GM")
    try:
        cfg["memory_gb"] = int(memory)
    except ValueError:
        cfg["memory_gb"] = 4

    if mc.get("cf_page_url"):
        slug = str(mc["cf_page_url"]).split("/modpacks/")[-1].split("/")[0].split("?")[0]
        cfg["cf_slug"] = slug.strip("/")
    if mc.get("cf_filename_matcher"):
        cfg["cf_filename_matcher"] = mc["cf_filename_matcher"]
    if mc.get("modrinth_projects"):
        projects = mc["modrinth_projects"].replace("\n", ",")
        cfg["modrinth_projects"] = ",".join(p.strip() for p in projects.split(",") if p.strip())

    return {**entry, "game": "minecraft", "config": cfg}


def _write(data: dict):
    _ensure_data_dir()
    with open(SERVERS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def list_servers() -> List[Server]:
    data = _read()
    return [Server(**s) for s in data["servers"]]


def get_server(server_id: str) -> Optional[Server]:
    data = _read()
    for s in data["servers"]:
        if s["id"] == server_id:
            return Server(**s)
    return None


def save_server(server: Server):
    data = _read()
    servers = data["servers"]
    for i, s in enumerate(servers):
        if s["id"] == server.id:
            servers[i] = json.loads(server.model_dump_json())
            _write(data)
            return
    servers.append(json.loads(server.model_dump_json()))
    _write(data)


def delete_server(server_id: str):
    data = _read()
    data["servers"] = [s for s in data["servers"] if s["id"] != server_id]
    _write(data)


def allocated_ports() -> List[int]:
    data = _read()
    return [s["port"] for s in data["servers"]]
