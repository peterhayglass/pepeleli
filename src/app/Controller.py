import platform, signal, atexit
import json
import sys
import discord
from discord import Message, TextChannel, Thread 
from discord.ext import commands
import asyncio
from types import FrameType
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
        
        ai_provider_type = self.config_manager.get_parameter('AI_PROVIDER_TYPE') 
        try:
            self.ai_model_provider = BaseAIModelProviderFactory.create(
                ai_provider_type, 
                self.config_manager, 
                self.logger)
        except ValueError as ve:
            self.logger.exception("an exception was raised trying to find the AIModelProvider to start", ve)
            sys.exit(1)
        except Exception as e:
            self.logger.exception("an unexpected exception was raised trying to start the AIModelProvider", e)
            sys.exit(1)
        
        self.event_handler = EventHandler(
            self.enqueue_message, 
            self.ai_model_provider.add_user_message,
            self.config_manager, 
            self.logger)

        _intents = discord.Intents.default()
        _intents.messages = True
        _intents.message_content = True  
        self.bot = commands.Bot(command_prefix='?', intents=_intents, description=self.DESCRIPTION)
        self.bot.add_listener(self.event_handler.on_message, 'on_message')
        self.bot.add_listener(self.on_ready, 'on_ready')
        self.bot.add_listener(self.on_close, 'on_close')
        
        self.event_loop = self.bot.loop
        
        if platform.system() != 'Windows':
            self.event_loop.add_signal_handler(signal.SIGINT, self.handle_shutdown)
            self.event_loop.add_signal_handler(signal.SIGTERM, self.handle_shutdown)
        else: #on Windows, for local testing
            atexit.register(self.win_handle_shutdown)
        

        self.queue: asyncio.Queue[Message] = asyncio.Queue()
        try:
            self.MONITOR_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("MONITOR_CHANNELS")
                )
        except Exception as e:
            self.logger.exception("Controller encounted an unexpected exception loading MONITOR_CHANNELS", e)
            raise


    def run(self) -> None:
        """Start the bot and connect to Discord API
           Called by the entrypoint
        """
        bot_token = self.config_manager.get_parameter('bot_token')
        self.bot.run(bot_token)
    

    async def on_ready(self) -> None:
        """Runs once the websocket is connected to Discord
        """
        self.processing_task = self.bot.loop.create_task(self.process_messages())
        """
        for channel_id in self.MONITOR_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                await channel.send("`pepeleli is online and listening to everything " 
                    "in this channel, but will only reply when tagged`")
            else:
                self.logger.error(f"Channel id {channel_id} in MONITOR_CHANNELS is invalid channel type")
                """


    async def on_close(self) -> None:
        """Runs when disconnecting from Discord
        """
        self.logger.error(f"Disconnected from Discord API")
        

    def handle_shutdown(self, signal: int, frame: FrameType) -> None:
        """This is run when we get SIGINT or SIGTERM, to shut down the bot
        """
        try:
            self.event_loop.run_until_complete(self.shutdown())
        finally:
            self.event_loop.close()


    def win_handle_shutdown(self) -> None:
        """This is run when we need to shut down the bot on Windows,
        such as a keyboard interrupt
        """

        for channel_id in self.MONITOR_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                self.event_loop.run_until_complete(channel.send("`pepeleli is going offline.  conversation history will be forgotten`"))
            else:
                self.logger.error(f"Channel id {channel_id} in MONITOR_CHANNELS is invalid channel type")


        self.event_loop.call_soon_threadsafe(self.processing_task.cancel)

        try:
            self.event_loop.run_until_complete(self.shutdown())
        finally:
            self.event_loop.close()


    async def shutdown(self) -> None:
        """clean up and shut down the bot
        """
        await self.bot.close()
        

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
            except asyncio.CancelledError as ce:
                self.logger.error(f"process_messages cancelled by a CancellationError: {ce}")
                raise
            except Exception as e:
                self.logger.exception(f"An error occurred while processing message {message.id}.", e)
            finally:
                self.queue.task_done()