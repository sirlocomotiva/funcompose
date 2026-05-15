from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class MinecraftConfig(BaseModel):
    type: Literal["VANILLA", "PAPER", "FABRIC"] = "PAPER"
    version: str = "LATEST"
    memory: str = "2G"
    max_players: int = 20
    motd: str = "A Minecraft Server"


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
