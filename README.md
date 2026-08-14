# funcompose
The docker compose with all files and configs for ez game hosting

## Minecraft Server - Prominence II [RPG]: Hasturian Era (v4.0.1)

### Quick Start with Docker Compose

To launch the Prominence II v4.0.1 Minecraft server directly:

```bash
docker compose -f docker-compose.prominence.yml up -d
```

Or using the main compose file with profile:

```bash
docker compose --profile prominence up -d
```

### Server Configuration

- **Modpack**: [Prominence II: Hasturian Era (v4.0.1)](https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era)
- **Extra Mods**: [Distant Horizons](https://modrinth.com/mod/distanthorizons) (`distanthorizons` via Modrinth integration) for Level-of-Detail (LOD) synchronization
- **Base Game Version**: Minecraft `1.20.1` (Fabric)
- **Default Port**: `25565`
- **Recommended Memory**: `8G` (or `6G` - `12G` depending on player count)
- **Image**: `itzg/minecraft-server:java17` (`TYPE: AUTO_CURSEFORGE`, `CF_FILENAME_MATCHER: "4.0.1"`, `MODRINTH_PROJECTS: distanthorizons`, `MODRINTH_ALLOWED_VERSION_TYPE: beta`)

### GameManager Web UI

To start the full GameManager panel (FastAPI backend + React frontend):

```bash
docker compose up -d
```

Access the web interface at `http://localhost:5173` (or port `8000` for backend API).
From the dashboard, you can create, start, stop, monitor, and view the live console of your servers including Prominence II v4.0.1.
