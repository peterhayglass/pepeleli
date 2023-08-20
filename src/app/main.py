from email.message import Message
import discord
from discord.ext import commands
import boto3


DESCRIPTION = "An experimental bot"
REGION = 'us-west-2'

_intents = discord.Intents.default()
_intents.messages = True
bot = commands.Bot(command_prefix='?', intents=_intents, description=DESCRIPTION)

@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        await message.channel.send("Hi")
    await bot.process_commands(message)

ssm_client = boto3.client('ssm', region_name=REGION)
bot_token = ssm_client.get_parameter(Name='bot_token', WithDecryption=True)
bot.run(bot_token['Parameter']['Value'])