from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class ServerCreate(BaseModel):
    name: str
    game_id: str
    config: dict = {}


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None


class Server(BaseModel):
    id: str
    name: str
    game: str = "minecraft"
    port: int
    config: dict[str, Any] = {}
    created_at: datetime
    status: str = "stopped"
