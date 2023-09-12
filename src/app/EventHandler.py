from IEventHandler import IEventHandler
from discord import Message
from typing import Awaitable, Callable
from ILogger import ILogger


class EventHandler(IEventHandler):
    """Implementation of the Event Handler"""
    def __init__(self, 
                enqueue_message: Callable[[Message], Awaitable[None]],
                logger: ILogger
                ) -> None:
        """Initialize the Event Handler
        
        Args: 
            enqueue_message (method reference): This method will be called 
            upon handling a new message, to put it into the processing queue
        
        Returns: None
        """
        self.enqueue_message = enqueue_message
        self.logger = logger


    async def on_message(self, message: Message) -> None:
        """Handle a received message"""
        self.logger.info(f"Received message: {message}\n Received message content: {message.content}")
        if message.author.bot: #don't respond to a message the bot itself sent
            return
        if message.guild is not None and message.guild.me in message.mentions:
            try:
                await self.enqueue_message(message)
            except Exception as e:
                self.logger.exception("enqueue_message threw an exception", e)
                pass