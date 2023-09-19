from abc import ABC, abstractmethod
from discord import Message

class IAIModelProvider(ABC):
    @abstractmethod
    async def get_response(self, message: Message) -> str:
        """Get a response from the AI model for the given user message.
        The AI also considers prior conversation history in deciding its response.
        
        The user message passed to get_response() is automatically added to history,
        so do not call add_user_message() separately for the same message.

        Args:
            message (Message): The user message to process.

        Returns:
            str: The response from the AI model.
        """
        pass


    @abstractmethod
    async def add_user_message(self, message: Message) -> None:
        """Add a new user message to the conversation history used by the AI,
        without requesting the AI to generate any response at this time.
        
        Args:
            message (Message): The user message to process.
        
        Returns: None
        """
        pass