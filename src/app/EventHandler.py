import json
import re
import time 
from typing import Awaitable, Callable

from discord import Message

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
        self.user_message_history: dict = {}

        try:
            self.RATE_LIMITS = json.loads(self.config_manager.get_parameter("RATE_LIMITS"))
            self.MONITOR_CHANNELS: list = json.loads(self.config_manager.get_parameter("MONITOR_CHANNELS"))
            self.BOT_USERNAME = self.config_manager.get_parameter("BOT_USERNAME")
            self.DEV_USER_ID = self.config_manager.get_parameter("DEV_USER_ID")
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

        if message.reference:
            message.content = f"[reply to: {message.reference.message_id}] " + message.content

        try:
            message.content = await self._replace_mentions(message)
        except Exception as e:
            self.logger.exception("replace_mentions threw an exception", e)
            pass
        
        if ((message.guild is not None and message.guild.me in message.mentions)
            or(self.BOT_USERNAME.lower() in message.content.lower())):
            #bot was mentioned
            await self._rl_update_message_history(message.author.id)

            if await self._should_rate_limit(message):
                await message.channel.send(f"{message.author.mention}, "
                    "you are being rate limited, your last message was ignored. "
                    "Please slow down.")    
                return
            
            try:
                await self.remember_message(message)
                await self.respond_to_message(message)
            except Exception as e:
                self.logger.exception("exception in on_message, bot mentioned.", e)
                await message.channel.send(
                    "`An unexpected error occurred communicating with the AI language model.  This has been logged.`")
                pass

        else: #bot was not mentioned
            try:
                await self.remember_message(message)
            except Exception as e:
                self.logger.exception("exception in on_message, bot not mentioned.", e)
                pass
                


    async def _replace_mentions(self, message: Message) -> str:
        """
        Replace user id mentions/tags in message content with usernames

        Args:
            message (Message): The message object containing the mentions.

        Returns:
            str: The updated message content
        """
        content = message.content
        pattern = re.compile(r'<@!?(\d+)>') #match mentions/tags like <@USER_ID> and <@!USER_ID>
        matches = pattern.findall(content)

        for user_id in matches:
            if not message.guild:
                return content
            user = message.guild.get_member(int(user_id))
            if user:
                user_mention = re.compile(r'(<@!?' + str(user_id) + r'>)')
                user_username = f'@{user.display_name}'
                content = user_mention.sub(user_username, content)

        return content


    async def _should_rate_limit(self, message: Message) -> bool:
        """
        Determine if a user should be rate-limited based on their message history

        Args:
            user_id (int): The user ID

        Returns:
            bool: True if the user should be rate-limited, otherwise False.
        """
        if message.author.id == self.DEV_USER_ID:
            return False
        
        now = time.time()
        user_history = self.user_message_history.get(message.author.id, [])

        for tier, limits in self.RATE_LIMITS.items():
            messages_in_interval = [
                timestamp for timestamp in user_history if now - timestamp < limits["interval"]
            ]
            if len(messages_in_interval) > limits["messages"]:
                self.logger.warning(f"User {message.author.name} is being rate-limited by {tier}")
                return True

        return False


    async def _rl_update_message_history(self, user_id: int) -> None:
        """For rate limiting purposes.
        Update the message history for a user by adding a timestamp for the latest message.
        Also cleans up old timestamps that are no longer needed for rate limiting checks.

        Args:
            user_id (int): The user's ID.

        Returns: None
        """
        developer_id = 281884580061904896
        if user_id == developer_id:
            return
        
        now = time.time()
        if user_id in self.user_message_history:
            longest_interval = max(limits["interval"] for _, limits in self.RATE_LIMITS.items())
            self.user_message_history[user_id] = [
                timestamp for timestamp in self.user_message_history[user_id] 
                    if now - timestamp <= longest_interval
            ]
            self.user_message_history[user_id].append(now)
        else:
            self.user_message_history[user_id] = [now]