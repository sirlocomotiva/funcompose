import docker
from docker.errors import NotFound

import games
from config import CONTAINER_PREFIX, VOLUME_PREFIX, PORT_RANGE_START, PORT_RANGE_END
from models.server import Server

client = docker.from_env()


def _container_name(server_id: str) -> str:
    return f"{CONTAINER_PREFIX}-{server_id}"


def get_container_status(server_id: str) -> str:
    try:
        container = client.containers.get(_container_name(server_id))
        return container.status  # running, exited, paused, etc.
    except NotFound:
        return "stopped"


def next_available_port(allocated: list[int], span: int = 1) -> int:
    # Reserve room for extra ports (base + i + 1) so ranges never overlap.
    used = set(allocated)
    for port in range(PORT_RANGE_START, PORT_RANGE_END - span + 2):
        if not any(p in used for p in range(port, port + span)):
            return port
    raise RuntimeError("No available ports in configured PORT_RANGE")


def create_and_start(server: Server):
    game = games.get_game(server.game)
    if not game:
        raise RuntimeError(f"Unknown game '{server.game}'")

    env = game["build_env"](server.config)

    ports = {
        f"{game['default_port']}/{game['port_protocol']}": server.port,
    }
    for i, extra in enumerate(game["extra_ports"] or []):
        ports[f"{extra['port']}/{extra['protocol']}"] = server.port + i + 1

    volumes = {}
    for i, path in enumerate(game["volumes"] or []):
        name = _volume_name(server.id) if i == 0 else f"{_volume_name(server.id)}-{i}"
        volumes[name] = {"bind": path, "mode": "rw"}

    try:
        mem_gb = int(server.config.get("memory_gb") or game["recommended_memory_gb"])
    except (TypeError, ValueError):
        mem_gb = game["recommended_memory_gb"] or 2

    client.containers.run(
        game["image"],
        name=_container_name(server.id),
        detach=True,
        platform="linux/amd64",
        environment=env,
        ports=ports,
        volumes=volumes,
        restart_policy={"Name": "unless-stopped"},
        mem_limit=f"{mem_gb}g",
        tty=True,
        stdin_open=True,
    )


def update_and_recreate(server: Server):
    """Apply new settings: remove the old container (data volumes survive), recreate."""
    try:
        container = client.containers.get(_container_name(server.id))
        container.stop(timeout=30)
        container.remove()
    except NotFound:
        pass
    create_and_start(server)


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
    prefix = _volume_name(server_id)
    for volume in client.volumes.list(filters={"name": prefix}):
        volume.remove()


def stream_logs(server_id: str):
    try:
        container = client.containers.get(_container_name(server_id))
        for chunk in container.logs(stream=True, follow=True, tail=100):
            yield chunk.decode("utf-8", errors="replace")
    except NotFound:
        yield f"Container for server {server_id} not found.\n"
