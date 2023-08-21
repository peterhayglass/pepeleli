from IEventHandler import IEventHandler
from discord import Message


class EventHandler(IEventHandler):
    """Implementation of the Event Handler"""

    async def on_message(self, message: Message) -> None:
        """Handle received messages"""
        print(f"Received message: {message}")
        print(f"Received message content: {message.content}")
        if message.author.bot: #don't respond to a message the bot itself sent
            return
        if message.guild is not None and message.guild.me in message.mentions:            
            if "open the pod bay doors" in message.content.lower():
                await message.channel.send(f"I'm afraid I can't do that, {message.author}. Like, I literally don't know how")
            else:
                await message.channel.send("Hi")
