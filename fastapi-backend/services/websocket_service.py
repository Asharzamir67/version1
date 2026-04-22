# services/websocket_service.py
from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # We use a copy to avoid issues if connections are removed during iteration
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                # If a connection is dead, remove it
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

    def broadcast_sync(self, message: dict):
        """Helper to broadcast from a non-async thread."""
        import asyncio
        # This only works if the loop is running (which it is for FastAPI)
        try:
            # Get the main event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
        except Exception as e:
            print(f"WS Broadcast failed: {e}")

# Global manager instance
manager = ConnectionManager()
