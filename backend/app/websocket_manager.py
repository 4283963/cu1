from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "sensor_data": [],
            "fan_status": []
        }

    async def connect(self, websocket: WebSocket, channel: str):
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        await websocket.accept()
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)

    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            message["timestamp"] = datetime.utcnow().isoformat()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        message["timestamp"] = datetime.utcnow().isoformat()
        await websocket.send_json(message)


manager = ConnectionManager()
