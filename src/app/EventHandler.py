from IEventHandler import IEventHandler
from discord import Message
from typing import Awaitable, Callable


class EventHandler(IEventHandler):
    """Implementation of the Event Handler"""
    
    def __init__(self, enqueue_message: Callable[[Message], Awaitable[None]]) -> None:
        """Initialize the Event Handler
        
        Args: 
            enqueue_message (method reference): This method will be called 
            upon handling a new message, to put it into the processing queue
        
        Returns: None
        """
        self.enqueue_message = enqueue_message

    async def on_message(self, message: Message) -> None:
        """Handle a received message"""
        print(f"Received message: {message}")
        print(f"Received message content: {message.content}")
        if message.author.bot: #don't respond to a message the bot itself sent
            return
        if message.guild is not None and message.guild.me in message.mentions:
            await self.enqueue_message(message)