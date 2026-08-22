import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

import store
import games
from models.server import Server, ServerCreate, ServerUpdate
from services import docker_service

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _with_status(server: Server) -> dict:
    d = server.model_dump()
    d["status"] = docker_service.get_container_status(server.id)
    return d


def _port_span(game_id: str) -> int:
    game = games.get_game(game_id)
    return len(game["extra_ports"] or []) + 1 if game else 1


@router.get("")
def list_servers():
    servers = store.list_servers()
    return [_with_status(s) for s in servers]


@router.post("", status_code=201)
def create_server(body: ServerCreate):
    if games.get_game(body.game_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown game '{body.game_id}'")

    try:
        config = games.validate_config(body.game_id, body.config)
    except games.ConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    port = docker_service.next_available_port(store.allocated_ports(), span=_port_span(body.game_id))

    server = Server(
        id=str(uuid.uuid4()),
        name=body.name,
        game=body.game_id,
        port=port,
        config=config,
        created_at=datetime.now(timezone.utc),
    )
    store.save_server(server)

    try:
        docker_service.create_and_start(server)
    except Exception as e:
        store.delete_server(server.id)
        raise HTTPException(status_code=500, detail=str(e))

    return _with_status(server)


@router.put("/{server_id}")
def update_server(server_id: str, body: ServerUpdate):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if body.name is not None and body.name.strip():
        server.name = body.name.strip()

    if body.config is not None:
        try:
            server.config = games.validate_config(server.game, body.config)
        except games.ConfigError as e:
            raise HTTPException(status_code=422, detail=str(e))
        try:
            docker_service.update_and_recreate(server)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    store.save_server(server)
    return _with_status(server)


@router.get("/{server_id}")
def get_server(server_id: str):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return _with_status(server)


@router.delete("/{server_id}", status_code=204)
def delete_server(server_id: str):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    docker_service.remove_container(server_id)
    store.delete_server(server_id)


@router.post("/{server_id}/start")
def start_server(server_id: str):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    try:
        docker_service.start_container(server_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _with_status(server)


@router.post("/{server_id}/stop")
def stop_server(server_id: str):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    docker_service.stop_container(server_id)
    return _with_status(server)


@router.post("/{server_id}/restart")
def restart_server(server_id: str):
    server = store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    try:
        docker_service.restart_container(server_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return _with_status(server)
