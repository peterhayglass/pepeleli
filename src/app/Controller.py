import sys
import discord
from discord import Message
from discord.ext import commands
import asyncio
from EventHandler import EventHandler
from ConfigManager import ConfigManager
from Logger import Logger
from ai.OobaAIModelProvider import OobaAIModelProvider
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
import ai.OobaAIModelProviderFactory
import ai.OpenAIModelProviderFactory


class Controller:
    """Controller class for the bot, orchestrates everything"""
    DESCRIPTION = "An experimental bot"


    def __init__(self) -> None:       
        self.logger = Logger()
        self.config_manager = ConfigManager(self.logger)
        self.event_handler = EventHandler(self.enqueue_message, self.logger)
        ai_provider_type = self.config_manager.get_parameter('AI_PROVIDER_TYPE') 
        try:
            self.ai_model_provider = BaseAIModelProviderFactory.create(ai_provider_type, self.config_manager, self.logger)
        except ValueError as ve:
            self.logger.error(str(ve))
            sys.exit(1)
        
        _intents = discord.Intents.default()
        _intents.messages = True
        _intents.message_content = True  
        self.bot = commands.Bot(command_prefix='?', intents=_intents, description=self.DESCRIPTION)
        self.bot.add_listener(self.event_handler.on_message, 'on_message')
        self.bot.add_listener(self.on_ready, 'on_ready')
        self.bot.add_listener(self.on_close, 'on_close')
        
        self.queue: asyncio.Queue[Message] = asyncio.Queue()


    def run(self) -> None:
        """Start the bot and connect to Discord API
           Called by the entrypoint
        """
        bot_token = self.config_manager.get_parameter('bot_token')
        self.bot.run(bot_token)
    

    async def on_ready(self) -> None:
        """Runs once the bot is connected and logged in to Discord
        """
        self.processing_task = asyncio.get_event_loop().create_task(self.process_messages())


    async def on_close(self) -> None:
        """Runs when disconnecting from Discord
        """
        if self.processing_task:
            self.processing_task.cancel()


    async def enqueue_message(self, message: Message) -> None:
        """Add a message to the processing queue"""
        await self.queue.put(message)


    async def process_messages(self) -> None:
        """Background task to process messages and send generated responses when ready"""
        while True:
            message = await self.queue.get()
            try:
                response = await self.ai_model_provider.get_response(message)
                await message.channel.send(response)
            except Exception as e:
                self.logger.exception(f"An error occurred while processing message {message.id}.", e)
            self.queue.task_done()