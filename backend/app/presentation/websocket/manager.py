"""
presentation/websocket/manager.py — WebSocket connection manager.
"""

import logging
import json
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for frontend clients.
    """

    def __init__(self):
        # Frontend browsers that listen for updates
        self.client_connections: List[WebSocket] = []

    async def connect_client(self, websocket: WebSocket) -> None:
        """Accept frontend WebSocket connection."""
        await websocket.accept()
        self.client_connections.append(websocket)
        logger.info(f"[WS] Client connected. Total clients: {len(self.client_connections)}")

    async def disconnect_client(self, websocket: WebSocket) -> None:
        """Remove disconnected frontend client."""
        if websocket in self.client_connections:
            self.client_connections.remove(websocket)
            logger.info(f"[WS] Client disconnected. Total clients: {len(self.client_connections)}")

    async def broadcast_clients(self, message: dict) -> None:
        """
        Broadcast message to all connected frontend clients.
        """
        if not self.client_connections:
            return

        msg_type = message.get("type", "unknown")
        # log only bulk_gps every 10 ticks to avoid spam
        if msg_type != "bulk_gps_update" or message.get("tick", 0) % 10 == 0:
            logger.info(f"[WS] Broadcasting {msg_type} to {len(self.client_connections)} clients")

        message_json = json.dumps(message, default=str)
        failed = []

        for conn in self.client_connections:
            try:
                await conn.send_text(message_json)
            except Exception as e:
                logger.debug(f"[WS] Broadcast failed for a client: {e}")
                failed.append(conn)

        for conn in failed:
            await self.disconnect_client(conn)

    async def broadcast(self, message: dict) -> None:
        await self.broadcast_clients(message)

    async def connect(self, websocket: WebSocket) -> None:
        await self.connect_client(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        await self.disconnect_client(websocket)

    def get_connection_count(self) -> int:
        return len(self.client_connections)


# Global manager instance
ws_manager = ConnectionManager()
