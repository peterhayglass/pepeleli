import platform, signal, atexit
import json
import sys
import asyncio
from typing import Dict, Tuple
from types import FrameType
from datetime import datetime

import discord
from discord import Message, TextChannel, Thread 
from discord.ext import commands

from EventHandler import EventHandler
from ConfigManager import ConfigManager
from Logger import Logger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.IAIModelProvider import IAIModelProvider
import ai.openai.OpenAIModelProviderFactory
import ai.openai.OpenAIInstructModelProviderFactory
import ai.vllm.VllmAIModelProviderFactory


class Controller:
    """Controller class for the bot, orchestrates everything"""
    DESCRIPTION = "An experimental bot"


    def __init__(self) -> None:
        self.logger = Logger()
        self.config_manager = ConfigManager(self.logger)

        try:
            self.MONITOR_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("MONITOR_CHANNELS"))
            self.ANNOUNCE_CHANNELS: list = json.loads(
                self.config_manager.get_parameter("ANNOUNCE_CHANNELS"))                
            self.MAX_CONCURRENT_AI_REQUESTS = int(
                self.config_manager.get_parameter("MAX_CONCURRENT_AI_REQUESTS"))
            self.AI_PROVIDER_TYPE = self.config_manager.get_parameter('AI_PROVIDER_TYPE')
            self.BOT_TOKEN = self.config_manager.get_parameter('BOT_TOKEN') 
        except Exception as e:
            self.logger.exception("Controller encounted an unexpected exception loading config", e)
            raise

        _intents = discord.Intents.default()
        _intents.messages = True
        _intents.message_content = True
        _intents.members = True
        self.bot = commands.Bot(command_prefix='?', intents=_intents, description=self.DESCRIPTION)

        self.bot.add_listener(self.on_ready, 'on_ready')
        self.bot.add_listener(self.on_close, 'on_close')
        
        self.DISCORD_MSG_MAX_LEN = 2000

        self.ai_request_semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_AI_REQUESTS)
        
        self.history_queues: Dict[int, asyncio.Queue[Tuple[Message, datetime]]] = {}
        #stores per-channel message history, keyed by channel id  
        

    def run(self) -> None:
        """Start the bot and connect to Discord API
           Called by the entrypoint
        """
              
        self.bot.run(self.BOT_TOKEN)
    

    async def on_ready(self) -> None:
        """Runs once the websocket is connected to Discord
        """
        if platform.system() != 'Windows':
            self.bot.loop.add_signal_handler(signal.SIGINT, self.handle_shutdown)
            self.bot.loop.add_signal_handler(signal.SIGTERM, self.handle_shutdown)
        else: #on Windows, for local testing
            atexit.register(self.win_handle_shutdown)

        try:
            self.ai_model_provider: IAIModelProvider = await BaseAIModelProviderFactory.create(
                self.AI_PROVIDER_TYPE, 
                self.config_manager, 
                self.logger,
                self.bot.loop
            )
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

        self.bot.add_listener(self.event_handler.on_message, 'on_message')

        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, 
                                       name=f"{await self.ai_model_provider.get_model_name()}"))        

        for channel_id in self.ANNOUNCE_CHANNELS:
            channel = self.bot.get_channel(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                await channel.send("`pepeleli is online and listening to everything " 
                    "in this channel, but I will only reply when tagged. "
                    "I will try to remember what happened before this, but I can't see anything that happened while I was offline. "
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
        if channel_id not in self.history_queues:
            self.history_queues[channel_id] = asyncio.Queue()
            self.bot.loop.create_task(
                self._process_channel_messages(channel_id, self.history_queues[channel_id]))
        enqueue_time = datetime.now()
        await self.history_queues[channel_id].put((message, enqueue_time))


    async def _process_single_message(self, message: Message, 
                                      enqueue_time: datetime
                                      ) -> None:
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
                    
                    response_time = datetime.now()
                    user_latency = (response_time - enqueue_time).total_seconds() * 1000  # in milliseconds
                    self.logger.debug(
                        f"response time for {message.id} was {int(user_latency)} ms")
                    
                    await self.ai_model_provider.add_bot_message(sent_msg)
            
            except Exception as e:
                self.logger.exception("an exception was raised trying to process a message for response", e)
                pass
            
            finally:
                channel_id = message.channel.id
                self.history_queues[channel_id].task_done()


    async def _process_channel_messages(self, channel_id: int, queue: asyncio.Queue) -> None:
        """Process messages from a given channel's message queue sequentially, 
        but without waiting on other channels."""
        while True:
            if not queue.empty():
                message, enqueue_time = await queue.get()
                
                start_time = datetime.now()
                start_timestamp = start_time.strftime("%H:%M:%S.%f")[:-3]
                self.logger.debug(f"starting processing for {message.id} at {start_timestamp}")

                await self._process_single_message(message, enqueue_time)

                end_time = datetime.now()
                end_timestamp = end_time.strftime("%H:%M:%S.%f")[:-3]
                time_delta = (end_time - start_time).total_seconds() * 1000  # in milliseconds
                self.logger.debug(f"finished processing for {message.id} at {end_timestamp}, took {int(time_delta)} ms")
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