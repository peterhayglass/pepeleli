import discord
from discord.ext import commands
from IConfigManager import IConfigManager
from IEventHandler import IEventHandler

class Controller:
    """Controller class for the bot, orchestrates everything"""

    DESCRIPTION = "An experimental bot"

    def __init__(self, config_manager: IConfigManager, event_handler: IEventHandler) -> None:
        _intents = discord.Intents.default()
        _intents.messages = True
        _intents.message_content = True    
        self.bot = commands.Bot(command_prefix='?', intents=_intents, description=self.DESCRIPTION)
        self.config_manager = config_manager
        self.event_handler = event_handler
        self.bot.add_listener(self.event_handler.on_message, 'on_message')

        # Registering the on_message event (will be implemented later)
        # self.bot.event(self.event_handler.on_message)

    def run(self) -> None:
        """Start the bot and connect to Discord API
           Called by the entrypoint
        """
        bot_token = self.config_manager.get_bot_token()
        self.bot.run(bot_token)
