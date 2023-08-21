from abc import ABC, abstractmethod
from discord import Message

class IAIModelProvider(ABC):
    @abstractmethod
    async def get_response(self, message: Message) -> str:
        """Get a response from the AI model for the given message.

        Args:
            message (Message): The message to process.

        Returns:
            str: The response from the AI model.
        """
        pass
