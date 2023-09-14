from IConfigManager import IConfigManager
from ai.IAIModelProvider import IAIModelProvider
from discord import Message
from typing import Any, AsyncGenerator
import websockets
from ILogger import ILogger
import json


class OobaAIModelProvider(IAIModelProvider):
    """AIModelProvider implementation for the oobabooga/text-generation-webui API
    See https://github.com/oobabooga/text-generation-webui
    
    """

    def __init__(self, 
                config_manager: IConfigManager,
                logger: ILogger
                ) -> None:
        self.AI_PROVIDER_HOST = config_manager.get_parameter('OOBA_AI_PROVIDER_HOST')
        self.URI = f'ws://{self.AI_PROVIDER_HOST}/api/v1/chat-stream'
        self.logger = logger
        self.history: dict = {}
        self.BLANK_HISTORY: dict =  {'internal': [], 'visible': []}
        return

    
    async def get_response(self, message: Message) -> str:
        """Get an AI response for a given user message, 
        also considering that user's recent chat history.

        Args: message (str): the user's message
        Returns: a string containing the AI's response
        """
        existing_history = self.history.get(message.author.id, self.BLANK_HISTORY)
        new_history = {}

        async for history_stream_item in self._stream_response(message, existing_history):
            new_history = history_stream_item

        accumulated_history = new_history
        self.history[message.author.id] = accumulated_history
        return accumulated_history['internal'][-1][1]


    async def _stream_response(self, message: Message, history: dict) -> AsyncGenerator[dict, None]:
        """Open a websocket to the AI model API, request and stream a response
        Args: 
            message (str): the user's latest message, to be responded to
            history (dict): the user's conversation history with the bot up to now
        Returns: 
            AsyncGenerator yielding a dictionary that contains the newly-updated chat history,
            including the newly generated AI response.
        """
        payload = self._construct_payload(message, history)
        try:
            async with websockets.connect(self.URI, ping_interval=None) as websocket: #type: ignore
                await websocket.send(json.dumps(payload))
                while True:
                    incoming_data = await websocket.recv()
                    incoming_data = json.loads(incoming_data)
                    match incoming_data['event']:
                        case 'text_stream':
                            yield incoming_data['history']
                        case 'stream_end':
                            return
        except Exception as e:
            self.logger.exception("An unexpected error occurred while communicating with the AI model.", e)
            return


    def _construct_payload(self, message: Message, history: dict) -> Any:
        """Prepare payload to go to the AI model API, containing user's message.
           Essentially a proof of concept implementation for now.
           Most of the hardcoded stuff I will make customizable later."""
        return {
            'user_input': message.content,
            'max_new_tokens': 300,
            'auto_max_new_tokens': False,
            'history': history,
            'mode': 'chat-instruct',
            'character': 'pepeleli',
            'instruction_template': 'pepe-synthia', 
            'your_name': message.author.display_name,
            'regenerate': False,
            '_continue': False,
            'chat_instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\n\n<|prompt|>',
            'preset': 'Mirostat',
            'do_sample': True,
            'seed': -1,
            'add_bos_token': True,
            'truncation_length': 2048,
            'ban_eos_token': False,
            'skip_special_tokens': True,
            'stopping_strings': []
        }