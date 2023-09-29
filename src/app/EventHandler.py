import json
import re
from discord import Message
from typing import Awaitable, Callable
from ILogger import ILogger
from IEventHandler import IEventHandler
from IConfigManager import IConfigManager


class EventHandler(IEventHandler):
    """Implementation of the Event Handler"""
    def __init__(self, 
                respond_to_message: Callable[[Message], Awaitable[None]],
                remember_message: Callable[[Message], Awaitable[None]],
                config_manager: IConfigManager,
                logger: ILogger
                ) -> None:
        """Initialize the Event Handler
        
        Args: 
            respond_to_message (method reference): Will be called upon handling
            a new user message which requires a response from the bot

            remember_message (method reference): Will be called upon handling
            a new user message which does NOT require a response from the bot, 
            but which should be added to the bot's memory/history.
        
        Returns: None
        """
        self.respond_to_message = respond_to_message
        self.remember_message = remember_message
        self.logger = logger
        self.config_manager = config_manager

        try:
            self.MONITOR_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("MONITOR_CHANNELS")
                )
            self.BOT_USERNAME = self.config_manager.get_parameter("BOT_USERNAME")
        except Exception as e:
            self.logger.exception("EventHandler encounted an unexpected exception loading config values", e)
            raise


    async def on_message(self, message: Message) -> None:
        """Handle a received message. Discord calls this when any message is sent.
        If the message "mentions" (tags) the bot, respond to it.
        Otherwise, just add it to the conversation history.
        """
        self.logger.debug(f"Received message: {message}\n Received message content: {message.content}")

        if message.channel.id not in self.MONITOR_CHANNELS:
            self.logger.debug(f"message handler received message in channel id {message.channel.id}, "
            f"not doing anything as we only monitor channels {self.MONITOR_CHANNELS}")
            return

        if message.author.bot: #don't need to handle a message the bot itself sent
            return
        
        try:
            message.content = await self.replace_mentions(message)
        except Exception as e:
            self.logger.exception("replace_mentions threw an exception", e)
            pass

        if ((message.guild is not None and message.guild.me in message.mentions)
            or(self.BOT_USERNAME.lower() in message.content.lower())):
            #bot was mentioned
            try:
                await self.respond_to_message(message)
            except Exception as e:
                self.logger.exception("respond_to_message threw an exception", e)
                pass
        else:
            try:
                await self.remember_message(message)
            except Exception as e:
                self.logger.exception("remember_message threw an exception", e)
                pass


    async def replace_mentions(self, message: Message) -> str:
        """replace mentions with int userids with a tag with a username
        so the LLM can understand when people tag/mention each other"""
        content = message.content
        pattern = re.compile(r'<@!?(\d+)>') #match mentions/tags like <@USER_ID> and <@!USER_ID>
        matches = pattern.findall(content)

        for user_id in matches:
            if not message.guild:
                return content
            user = message.guild.get_member(int(user_id))
            if user:
                user_mention = f'<@{user_id}>'
                user_username = f'@{user.display_name}'
                content = content.replace(user_mention, user_username)

        return content