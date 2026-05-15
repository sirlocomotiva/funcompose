import asyncio
import threading
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import store
from services import docker_service

router = APIRouter(tags=["console"])


@router.websocket("/api/servers/{server_id}/console")
async def console(websocket: WebSocket, server_id: str):
    await websocket.accept()

    server = store.get_server(server_id)
    if not server:
        await websocket.send_text("Server not found.\n")
        await websocket.close()
        return

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _produce():
        try:
            for line in docker_service.stream_logs(server_id):
                asyncio.run_coroutine_threadsafe(queue.put(line), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    thread = threading.Thread(target=_produce, daemon=True)
    thread.start()

    try:
        while True:
            line = await queue.get()
            if line is None:
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
