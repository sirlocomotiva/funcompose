import os
import docker
from docker.errors import NotFound, APIError
from typing import Literal

from config import CONTAINER_PREFIX, VOLUME_PREFIX, PORT_RANGE_START, PORT_RANGE_END
from models.server import Server

client = docker.from_env()

MINECRAFT_IMAGE = os.getenv("MINECRAFT_IMAGE", "itzg/minecraft-server:java17")
PROMINENCE_DEFAULT_URL = (
    "https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era"
)


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
    server_type = server.minecraft.type
    cf_url = server.minecraft.cf_page_url

    if server_type == "PROMINENCE_II":
        server_type = "AUTO_CURSEFORGE"
        if not cf_url:
            cf_url = PROMINENCE_DEFAULT_URL

    if cf_url and "/download/" in cf_url and server_type == "AUTO_CURSEFORGE":
        cf_url = cf_url.split("/download/")[0]

    env = {
        "EULA": "TRUE",
        "TYPE": server_type,
        "VERSION": server.minecraft.version,
        "MEMORY": server.minecraft.memory,
        "MAX_PLAYERS": str(server.minecraft.max_players),
        "MOTD": server.minecraft.motd,
        "ONLINE_MODE": "FALSE",
    }

    if cf_url:
        env["CF_PAGE_URL"] = cf_url
    if server.minecraft.cf_file_id:
        env["CF_FILE_ID"] = server.minecraft.cf_file_id
    if server.minecraft.cf_slug:
        env["CF_SLUG"] = server.minecraft.cf_slug
    if server.minecraft.cf_filename_matcher:
        env["CF_FILENAME_MATCHER"] = server.minecraft.cf_filename_matcher
    elif server.minecraft.modpack_name and "4.0.1" in server.minecraft.modpack_name:
        env["CF_FILENAME_MATCHER"] = "4.0.1"

    cf_api_key = server.minecraft.cf_api_key or os.getenv("CF_API_KEY")
    if cf_api_key:
        env["CF_API_KEY"] = cf_api_key

    modrinth_items = []
    if server.minecraft.modrinth_projects:
        modrinth_items.extend(server.minecraft.modrinth_projects.replace("\n", ",").split(","))

    if server.minecraft.include_distant_horizons or (
        server.minecraft.modpack_name and "prominence" in server.minecraft.modpack_name.lower()
    ):
        if not any(x.strip() in ["distanthorizons", "distant-horizons"] for x in modrinth_items):
            modrinth_items.append("distanthorizons")

    if modrinth_items:
        clean_modrinth = ",".join(filter(None, [m.strip() for m in modrinth_items]))
        if clean_modrinth:
            env["MODRINTH_PROJECTS"] = clean_modrinth
            env["MODRINTH_ALLOWED_VERSION_TYPE"] = (
                server.minecraft.modrinth_allowed_version_type or "beta"
            )

    if server.minecraft.curseforge_files:
        env["CURSEFORGE_FILES"] = server.minecraft.curseforge_files
    if server.minecraft.extra_mods:
        env["MODS"] = server.minecraft.extra_mods

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
