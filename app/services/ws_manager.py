import time
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[WebSocket, int]]] = defaultdict(list)

    async def connect(self, user_id: str, websocket: WebSocket, exp: int) -> None:
        await websocket.accept()
        self._subscribers[user_id].append((websocket, exp))

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        connections = self._subscribers.get(user_id, [])
        self._subscribers[user_id] = [entry for entry in connections if entry[0] is not websocket]
        if not self._subscribers[user_id]:
            self._subscribers.pop(user_id, None)

    async def broadcast(self, user_id: str, message: dict) -> None:
        now = int(time.time())
        stale: list[WebSocket] = []
        for websocket, exp in list(self._subscribers.get(user_id, [])):
            if exp <= now:
                stale.append(websocket)
                await websocket.close(code=1008, reason="Token expired")
                continue
            await websocket.send_json(message)

        for websocket in stale:
            self.disconnect(user_id, websocket)
