import json
import os
from typing import List
from datetime import datetime

from config import SERVERS_FILE, DATA_PATH
from models.server import Server


def _ensure_data_dir():
    os.makedirs(DATA_PATH, exist_ok=True)


def _read() -> dict:
    _ensure_data_dir()
    if not os.path.exists(SERVERS_FILE):
        return {"servers": []}
    with open(SERVERS_FILE, "r") as f:
        return json.load(f)


def _write(data: dict):
    _ensure_data_dir()
    with open(SERVERS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def list_servers() -> List[Server]:
    data = _read()
    return [Server(**s) for s in data["servers"]]


def get_server(server_id: str) -> Server | None:
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
