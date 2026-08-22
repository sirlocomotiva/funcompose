# funcompose

Self-hosted game server manager — run **Minecraft, Valheim, Terraria and 7 Days to Die** servers from a single web dashboard. Works on **Windows, macOS and Linux** via Docker.

<p>
<img alt="games" src="https://img.shields.io/badge/games-Minecraft%20·%20Valheim%20·%20Terraria%20·%207DtD-green">
</p>

## Quick Start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine + compose plugin (Linux).
2. From this folder:

```bash
# macOS / Linux
./start.sh

# Windows
start.bat
```

or manually:

```bash
docker compose up -d --build
```

3. Open the dashboard: **http://localhost:5173**

## What you get

- 🎮 **Pick a game, get a server** — a 2-step wizard: choose Minecraft / Valheim / Terraria / 7 Days to Die (Hytale slot ready for launch), then fill in name, RAM, players, passwords…
- ⛏️ **Full Minecraft flexibility** — Vanilla, Paper, Fabric, Forge, any **CurseForge modpack** (paste the URL), any **Modrinth modpack**, extra Modrinth mods, server-pack zips or raw `.jar` URLs.
- 🔧 **Everything is a variable** — RAM per server, versions, difficulty, MOTD, max players, online-mode, seeds, worlds, passwords. Edit any of it later from "Edit Settings" (container recreates, world data survives).
- 📺 **Live console** — every server has a real-time log viewer.
- 💾 **Persistent by design** — each server's data lives in a Docker-managed volume; stop/start/recreate as you like.

## Supported games & defaults

| Game | Image | Default port | Min RAM | Notes |
|---|---|---|---|---|
| Minecraft | `itzg/minecraft-server` | 25565/tcp | 2 GB | Modpacks need a free [CurseForge API key](https://console.curseforge.com/) in `.env` |
| Valheim | `lloesche/valheim-server` | 2456–2457/udp | 2 GB | Join password required |
| Terraria | `ryshe/terraria` | 7777/tcp | 1 GB | World auto-created on first start |
| 7 Days to Die | `vinanrra/7dtd-server` | 26900–26902 | 6 GB | Needs ~8 GB to feel good |
| Hytale | — | — | — | Placeholder until official servers ship |

Ports are assigned automatically from your configured range (see `.env.example`). For internet play, forward the game's ports on your router.

## Configuration

Copy `.env.example` → `.env` and tweak:

```ini
FRONTEND_PORT=5173
BACKEND_PORT=8000
PORT_RANGE_START=7777   # auto-assigned server ports live here
PORT_RANGE_END=27000
CF_API_KEY=             # only needed for CurseForge modpacks
```

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌ docker.sock ┐
│ React + Vite │ ──▶ │ FastAPI backend │ ──▶ │  containers  │
│  :5173       │     │  :8000          │     │ MC/VH/TR/7D  │
└──────────────┘     └─────────────────┘     └──────────────┘
```

- `backend/` — FastAPI + [docker SDK](https://docker-py.readthedocs.io/). The game catalog lives in one file (`backend/games.py`): image, ports, volumes, env-var mapping and the form schema per game. Adding a game = adding an entry there; frontend forms render themselves from `GET /api/games`.
- `frontend/` — React + Tailwind. Dashboard with status polling, creation wizard driven entirely by the API's field definitions, live WebSocket console.
- Server metadata: `/data/servers.json` (volume). Worlds/saves: Docker volumes `gamemanager-data-*`.

### Adding a new game

1. Add an entry to `GAMES` in `backend/games.py` (image, ports, volumes, `build_env()`, `fields`).
2. Done — the UI picks it up automatically.

## Dev mode

```bash
docker compose up -d          # hot-reloading backend (:8000/docs) & frontend (:5173)
```

Backend logs: `docker compose logs -f backend`. Reset everything: `docker compose down -v` (**wipes all server worlds**).

## Migrating from the old version

Old Minecraft-only records in `servers.json` are auto-migrated on first boot. The old static `prominence` / `vanilla` compose services were removed — create servers from the UI instead; your existing `./servers/prominence` files can be copied into the new volume if needed:

```bash
docker volume create gamemanager-data-<server-id>
docker cp ./servers/prominence/. <container>:/data/
```
