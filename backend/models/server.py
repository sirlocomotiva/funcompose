from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MinecraftConfig(BaseModel):
    type: str = "PAPER"
    version: str = "LATEST"
    memory: str = "2G"
    max_players: int = 20
    motd: str = "A Minecraft Server"
    cf_page_url: Optional[str] = None
    cf_file_id: Optional[str] = None
    cf_slug: Optional[str] = None
    cf_filename_matcher: Optional[str] = None
    cf_api_key: Optional[str] = None
    modpack_name: Optional[str] = None
    modrinth_projects: Optional[str] = None
    modrinth_allowed_version_type: Optional[str] = None
    curseforge_files: Optional[str] = None
    extra_mods: Optional[str] = None
    include_distant_horizons: bool = False
    include_xaero_sync: bool = False


class ServerCreate(BaseModel):
    name: str
    minecraft: MinecraftConfig = MinecraftConfig()


class Server(BaseModel):
    id: str
    name: str
    game: str = "minecraft"
    port: int
    minecraft: MinecraftConfig
    created_at: datetime
    status: str = "stopped"
