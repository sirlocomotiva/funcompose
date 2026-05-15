import os

DATA_PATH = os.getenv("DATA_PATH", "/data")
SERVERS_FILE = os.path.join(DATA_PATH, "servers.json")

PORT_RANGE_START = 25565
PORT_RANGE_END = 25665

CONTAINER_PREFIX = "gamemanager"
VOLUME_PREFIX = "gamemanager-data"
