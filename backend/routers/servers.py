import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

import store
from models.server import Server, ServerCreate
from services import docker_service

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _with_status(server: Server) -> dict:
    d = server.model_dump()
    d["status"] = docker_service.get_container_status(server.id)
    return d


@router.get("")
def list_servers():
    servers = store.list_servers()
    return [_with_status(s) for s in servers]


@router.post("", status_code=201)
def create_server(body: ServerCreate):
    allocated = store.allocated_ports()
    port = docker_service.next_available_port(allocated)

    server = Server(
        id=str(uuid.uuid4()),
        name=body.name,
        port=port,
        minecraft=body.minecraft,
        created_at=datetime.now(timezone.utc),
    )
    store.save_server(server)

    try:
        docker_service.create_and_start(server)
    except Exception as e:
        store.delete_server(server.id)
        raise HTTPException(status_code=500, detail=str(e))

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
