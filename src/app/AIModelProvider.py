from IConfigManager import IConfigManager
from IAIModelProvider import IAIModelProvider
from discord import Message
from typing import Any, Dict, AsyncGenerator
import websockets
from ILogger import ILogger
import json


class AIModelProvider(IAIModelProvider):
    """AIModelProvider implementation for the oobabooga/text-generation-webui API
    See https://github.com/oobabooga/text-generation-webui
    
    """

    def __init__(self, 
                config_manager: IConfigManager,
                logger: ILogger
                ) -> None:
        self.AI_PROVIDER_HOST = config_manager.get_parameter('AI_PROVIDER_HOST')
        self.URI = f'ws://{self.AI_PROVIDER_HOST}/api/v1/chat-stream'
        self.logger = logger
        return

    async def get_response(self, message: Message) -> str:
        accumulated_history = {}
        async for new_history in self._stream_response(message):
            accumulated_history = new_history
        return accumulated_history['internal'][-1][1]


    async def _stream_response(self, message: Message) -> AsyncGenerator[Dict[str, Any], None]:
        """Open a websocket to the AI model API, request and stream a response
        """
        payload = self._construct_payload(message)
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


    def _construct_payload(self, message: Message) -> Any:
        """Prepare payload to go to the AI model API, containing user's message.
           Essentially a proof of concept implementation for now.
           Most of the hardcoded stuff I will make customizable later."""
        history: dict = {'internal': [], 'visible': []}
        return {
            'user_input': message.content,
            'max_new_tokens': 250,
            'auto_max_new_tokens': False,
            'history': history,
            'mode': 'chat-instruct',
            'character': 'pepeleli',
            'instruction_template': 'pepeleli', 
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
