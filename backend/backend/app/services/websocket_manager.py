from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(jsonable_encoder(message))

    async def broadcast(self, message: dict):
        encoded_message = jsonable_encoder(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_json(encoded_message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
