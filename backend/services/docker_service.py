import docker
from docker.errors import NotFound, APIError
from typing import Literal

from config import CONTAINER_PREFIX, VOLUME_PREFIX, PORT_RANGE_START, PORT_RANGE_END
from models.server import Server

client = docker.from_env()

MINECRAFT_IMAGE = "itzg/minecraft-server"


def _container_name(server_id: str) -> str:
    return f"{CONTAINER_PREFIX}-{server_id}"


def _volume_name(server_id: str) -> str:
    return f"{VOLUME_PREFIX}-{server_id}"


def get_container_status(server_id: str) -> str:
    try:
        container = client.containers.get(_container_name(server_id))
        return container.status  # running, exited, paused, etc.
    except NotFound:
        return "stopped"


def next_available_port(allocated: list[int]) -> int:
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port not in allocated:
            return port
    raise RuntimeError("No available ports in range")


def create_and_start(server: Server):
    env = {
        "EULA": "TRUE",
        "TYPE": server.minecraft.type,
        "VERSION": server.minecraft.version,
        "MEMORY": server.minecraft.memory,
        "MAX_PLAYERS": str(server.minecraft.max_players),
        "MOTD": server.minecraft.motd,
        "ONLINE_MODE": "FALSE",
    }
    client.containers.run(
        MINECRAFT_IMAGE,
        name=_container_name(server.id),
        detach=True,
        platform="linux/amd64",
        environment=env,
        ports={"25565/tcp": server.port},
        volumes={_volume_name(server.id): {"bind": "/data", "mode": "rw"}},
        restart_policy={"Name": "unless-stopped"},
        tty=True,
        stdin_open=True,
    )


def start_container(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        container.start()
    except NotFound:
        raise RuntimeError(f"Container for server {server_id} not found")


def stop_container(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        container.stop(timeout=30)
    except NotFound:
        pass


def restart_container(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        container.restart(timeout=30)
    except NotFound:
        raise RuntimeError(f"Container for server {server_id} not found")


def remove_container(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        container.stop(timeout=10)
        container.remove()
    except NotFound:
        pass
    try:
        volume = client.volumes.get(_volume_name(server_id))
        volume.remove()
    except NotFound:
        pass


def stream_logs(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        for chunk in container.logs(stream=True, follow=True, tail=100):
            yield chunk.decode("utf-8", errors="replace")
    except NotFound:
        yield f"Container for server {server_id} not found.\n"
