from abc import ABC, abstractmethod
from discord import Message


class IEventHandler(ABC):
    """Interface for the Event Handler"""

    @abstractmethod
    async def on_message(self, message: Message) -> None:
        """Handle received messages"""
        pass