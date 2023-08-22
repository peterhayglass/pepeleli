from IConfigManager import IConfigManager
from IAIModelProvider import IAIModelProvider
from discord import Message
from typing import Any
import aiohttp


class AIModelProvider(IAIModelProvider):

    def __init__(self, config_manager: IConfigManager) -> None:
        self.AI_PROVIDER_HOST = config_manager.get_parameter('AI_PROVIDER_HOST')
        self.URI = f'https://{self.AI_PROVIDER_HOST}/api/v1/chat'
        return


    async def get_response(self, message: Message) -> str:
        """Makes a request to the AI model
        """
        payload = self._construct_payload(message)
        timeout = aiohttp.ClientTimeout(total=40)  # 40 seconds.  LLMs on cheap hardware are slow
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.URI, json=payload) as response:
                    response.raise_for_status()  # Raises an exception if the HTTP status is an error
                    response_json = await response.json()
                    return response_json['results'][0]['history']['internal'][-1][1]

        except aiohttp.ClientError as e:
            print(f"A ClientError occurred while communicating with the AI model: {e}")
            return "A ClientError occurred while communicating with the AI model."

        except Exception as e:
            print(f"An unexpected error while communicating with the AI model: {e}")
            return "An unexpected error occurred while communicating with the AI model."


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
