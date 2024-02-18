from litellm import completion, acompletion
from ...core.config import NotificationConfiguration
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, config: NotificationConfiguration):
        self._config = config
        self.socket_app = None

    async def send_notification(self, title, body, type, payload=None):
        logger.info(f"Sending notification: {title} {body} {type} {payload}")
        if self.socket_app:
            await self.socket_app.emit_message(type, payload)

    async def emit_message(self, type: str, payload=None):
        await self.socket_app.emit_message(type, payload)