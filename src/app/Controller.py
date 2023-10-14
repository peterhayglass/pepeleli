import platform, signal, atexit
import json
import sys
import asyncio
from typing import Dict
from types import FrameType
from datetime import datetime

import discord
from discord import Message, TextChannel, Thread 
from discord.ext import commands

from EventHandler import EventHandler
from ConfigManager import ConfigManager
from Logger import Logger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
import ai.openai.OpenAIModelProviderFactory
import ai.openai.OpenAIInstructModelProviderFactory
import ai.vllm.VllmAIModelProviderFactory


class Controller:
    """Controller class for the bot, orchestrates everything"""
    DESCRIPTION = "An experimental bot"


    def __init__(self) -> None:

        self.logger = Logger()
        self.config_manager = ConfigManager(self.logger)
        
        self.AI_PROVIDER_TYPE = self.config_manager.get_parameter('AI_PROVIDER_TYPE') 
        try:
            self.ai_model_provider = BaseAIModelProviderFactory.create(
                self.AI_PROVIDER_TYPE, 
                self.config_manager, 
                self.logger)
        except ValueError as ve:
            self.logger.exception("a ValueError was raised trying to start the AIModelProvider ", ve)
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
        _intents.members = True
          
        self.bot = commands.Bot(command_prefix='?', intents=_intents, description=self.DESCRIPTION)
        self.bot.add_listener(self.event_handler.on_message, 'on_message')
        self.bot.add_listener(self.on_ready, 'on_ready')
        self.bot.add_listener(self.on_close, 'on_close')
        
        self.DISCORD_MSG_MAX_LEN = 2000
        try:
            self.MONITOR_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("MONITOR_CHANNELS"))
            self.ANNOUNCE_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("ANNOUNCE_CHANNELS"))                
            self.MAX_CONCURRENT_AI_REQUESTS = int(
                self.config_manager.get_parameter("MAX_CONCURRENT_AI_REQUESTS"))
        except Exception as e:
            self.logger.exception("Controller encounted an unexpected exception loading channels config", e)
            raise

        self.ai_request_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_AI_REQUESTS)
        self.queues: Dict[int,asyncio.Queue[Message]] = {}


    def run(self) -> None:
        """Start the bot and connect to Discord API
           Called by the entrypoint
        """
        bot_token = self.config_manager.get_parameter('bot_token')
        self.bot.run(bot_token)
    

    async def on_ready(self) -> None:
        """Runs once the websocket is connected to Discord
        """
        if platform.system() != 'Windows':
            self.bot.loop.add_signal_handler(signal.SIGINT, self.handle_shutdown)
            self.bot.loop.add_signal_handler(signal.SIGTERM, self.handle_shutdown)
        else: #on Windows, for local testing
            atexit.register(self.win_handle_shutdown)
        
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, 
                                       name=f"{await self.ai_model_provider.get_model_name()}"))        

        for channel_id in self.ANNOUNCE_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                await channel.send("`pepeleli is online and listening to everything " 
                    "in this channel, but I will only reply when tagged. "
                    "I can't remember any conversations prior to this. "
                    f"[Provider type: {self.AI_PROVIDER_TYPE}]"
                    f"[Model: {await self.ai_model_provider.get_model_name()}]`")
            else:
                self.logger.error(f"Channel id {channel_id} in MONITOR_CHANNELS is invalid channel type")
                

    async def on_close(self) -> None:
        """Runs when disconnecting from Discord
        """
        self.logger.error(f"Disconnected from Discord API")
        

    def handle_shutdown(self, signal: int, frame: FrameType) -> None:
        """This is run when we get SIGINT or SIGTERM, to shut down the bot
        """
        try:
            self.bot.loop.run_until_complete(self.shutdown())
        finally:
            self.bot.loop.close()


    def win_handle_shutdown(self) -> None:
        """This is run when we need to shut down the bot on Windows,
        such as a keyboard interrupt
        """
        try:
            self.bot.loop.run_until_complete(self.shutdown())
        finally:
            self.bot.loop.close()


    async def shutdown(self) -> None:
        """clean up and shut down the bot
        """
        await self.bot.close()
        

    async def enqueue_message(self, message: Message) -> None:
        """Add a message to the processing queue"""
        channel_id = message.channel.id
        if channel_id not in self.queues:
            self.queues[channel_id] = asyncio.Queue()
            self.bot.loop.create_task(
                self._process_channel_messages(channel_id, self.queues[channel_id]))
        await self.queues[channel_id].put(message)


    async def _process_single_message(self, message: Message) -> None:
        """helper function to process a single message and send a response
        called by process_messages() which handles consuming from queues"""
        async with self.ai_request_semaphore:
            try:
                response = await self.ai_model_provider.get_response(message)
                if not response:
                    return
                chunked_response = self._chunk_response(response)
                for response in chunked_response:
                    sent_msg = await message.channel.send(response, reference=message)
                    await self.ai_model_provider.add_bot_message(sent_msg)
            finally:
                channel_id = message.channel.id
                self.queues[channel_id].task_done()


    async def _process_channel_messages(self, channel_id: int, queue: asyncio.Queue) -> None:
        """Process messages from a given channel's message queue sequentially, 
        but without waiting on other channels."""
        while True:
            if not queue.empty():
                message = await queue.get()
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.logger.debug(f"starting processing for {message.id} at {timestamp}")
                
                await self._process_single_message(message)

                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                self.logger.debug(f"finished processing for {message.id} at {timestamp}")
            else:
                await asyncio.sleep(0.1)


    def _chunk_response(self, response: str) -> list[str]:
        """Split the AI response into chunks small enough to fit in a discord message,
        so we can send long responses as multiple messages
        """
        chunks = []
        for i in range(0, len(response), self.DISCORD_MSG_MAX_LEN):
            chunk = response[i : i + self.DISCORD_MSG_MAX_LEN]
            chunks.append(chunk)
        return chunks