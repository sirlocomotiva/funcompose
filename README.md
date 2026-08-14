# funcompose
The docker compose with all files and configs for ez game hosting

## Minecraft Servers (Docker Compose)

### Quick Start

All services are consolidated into a single `docker-compose.yml` file using compose profiles:

- **Launch Prominence II (v4.0.1)**:
  ```bash
  docker compose --profile prominence up -d
  ```

- **Launch Vanilla Minecraft Server**:
  ```bash
  docker compose --profile vanilla up -d
  ```

- **Launch GameManager Web Panel (UI + API)**:
  ```bash
  docker compose up -d
  ```

- **Launch Everything**:
  ```bash
  docker compose --profile all up -d
  ```

### Server Configuration & Filesystem Storage

Server data directories are directly bind-mounted to the host filesystem where docker compose is launched:
- **Prominence II files**: `./servers/prominence/` (`server.properties`, `config/`, `mods/`, `world/`, logs)
- **Vanilla files**: `./servers/vanilla/`

You can directly modify server configurations, edit `server.properties`, tweak mod config files in `./servers/prominence/config/`, or add/remove mods directly on the host filesystem.

- **Prominence II RPG [Hasturian Era] (v4.0.1)**:
  - **Service**: `prominence` (container: `prominence`)
  - **Directory**: `./servers/prominence`
  - **Modpack**: [Prominence II: Hasturian Era (v4.0.1)](https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era)
  - **Extra Mods**:
    - [Distant Horizons](https://modrinth.com/mod/distanthorizons) (`distanthorizons`) &mdash; Level-of-Detail (LOD) synchronization for extended render distances
    - [Xaero's Maps: Multiplayer+](https://modrinth.com/mod/xaeros-maps-multiplayer-plus) (`xaeros-maps-multiplayer-plus`) &mdash; Real-time world map exploration and waypoint synchronization across all players (pairs with client-side [XaeroPlus](https://modrinth.com/mod/xaeroplus))
  - **Image**: `itzg/minecraft-server:java17` (`TYPE: AUTO_CURSEFORGE`, `CF_FILENAME_MATCHER: "4.0.1"`, `MODRINTH_PROJECTS: distanthorizons,xaeros-maps-multiplayer-plus`, `MODRINTH_ALLOWED_VERSION_TYPE: beta`)
  - **Memory**: `8G` (Fabric 1.20.1)

- **Vanilla Minecraft**:
  - **Service**: `vanilla` (container: `vanilla`)
  - **Directory**: `./servers/vanilla`
  - **Image**: `itzg/minecraft-server:java21` (`TYPE: VANILLA`, `VERSION: LATEST`)
  - **Memory**: `2G`

### GameManager Web UI

To start the full GameManager panel (FastAPI backend + React frontend):

```bash
docker compose up -d
```

Access the web interface at `http://localhost:5173` (or port `8000` for backend API).
From the dashboard, you can create, start, stop, monitor, and view the live console of your servers including Prominence II v4.0.1.
