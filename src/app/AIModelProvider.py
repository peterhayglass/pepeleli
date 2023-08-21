from IAIModelProvider import IAIModelProvider
from discord import Message

class AIModelProvider(IAIModelProvider):

    def __init__(self) -> None:
        return

    async def get_response(self, message: Message) -> str:
        """Get a response from the AI model for the given message.

        Args:
            message (Message): The message to process.

        Returns:
            str: The response from the AI model.
        """
        return f"Hello, {message.author}! I'm an if statement masquerading as an AI model."
