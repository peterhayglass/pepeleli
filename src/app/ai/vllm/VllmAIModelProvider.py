from asyncio import AbstractEventLoop
from collections import deque
import json
from typing import Optional, List

from discord import Message

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
from ai.vllm.VLLMClient import VLLMClient
from IHistoryManager import IHistoryManager, HistoryItem
from HistoryManager import HistoryManager


class VllmAIModelProvider(IAIModelProvider):
    """AI model provider implementation for vLLM
    see: https://github.com/vllm-project/vllm
    """

    def __init__(self, 
                 config_manager: IConfigManager,
                 logger: ILogger) -> None:
        
        self.logger = logger
        self.config_manager = config_manager

        try:
            self.BOT_USERNAME = self.config_manager.get_parameter("BOT_USERNAME")
            self.MAX_CONTEXT_LEN = int(self.config_manager.get_parameter("VLLM_MAX_CONTEXT_LEN"))
            self.RESPONSE_MODEL = self.config_manager.get_parameter("VLLM_RESPONSE_MODEL")
            self.STOP_SEQUENCES: list[str] = json.loads(self.config_manager.get_parameter("STOP_SEQUENCES"))
            _host = self.config_manager.get_parameter("VLLM_AI_PROVIDER_HOST")
            _port = int(self.config_manager.get_parameter("VLLM_AI_PROVIDER_PORT"))
            _api_key = self.config_manager.get_parameter("VLLM_API_KEY")
        except ValueError as ve:
            self.logger.exception("error loading VLLMAIModelProvider configuration: ", ve)
            raise

        self.SYSTEM_MSG = f"""### Instruction:
        [character info]: {self.BOT_USERNAME} is an eccentric character, chill, friendly and laid back by default, but moody and opinionated and not shy about sharing opinions.  {self.BOT_USERNAME} can even get straight up unhinged if somebody says something that pushes his buttons, is fairly jaded and cynical in general but also has a sense of humour.  He is talking to his friends so he is honest, even a bit fuckin vulgar at times.  Despite the very rough edges, {self.BOT_USERNAME} has a good heart. 
        continue the chat dialogue below by writing only a single reply in character as {self.BOT_USERNAME}. Do not write messages for other users. Do not tag users with the @ symbol. Do not write narration, system messages or anything other than dialogue from {self.BOT_USERNAME}. """
        self.INSTRUCTION = ""#f"### Instruction: "
        self.REPLY_INSTRUCTION = f" Do not mention message ID numbers or specifically say you are replying, however do consider that {self.BOT_USERNAME} is replying to messageID:"
        self.RESPONSE_PRIMER = "### Response:\n"
        self.MAX_TOKENS_RESPONSE = 250
        self.IGNORE_EMOJI = '❌'
        
        self.vllm = VLLMClient(_host, _port, _api_key)
        
    
    async def _init_async(self) -> None:
        """Finish the parts of initialization that require async operations"""
        _prompt_tokens = (await self._count_tokens_str(self.SYSTEM_MSG) + 
                            await self._count_tokens_str(self.INSTRUCTION) +
                            await self._count_tokens_str(self.REPLY_INSTRUCTION) +
                            await self._count_tokens_str(self.RESPONSE_PRIMER))
        self.MAX_HISTORY_LEN = self.MAX_CONTEXT_LEN - (self.MAX_TOKENS_RESPONSE + _prompt_tokens)

        self.history_manager: IHistoryManager = HistoryManager(
            self._count_tokens_list,
            self._format_msg,
            self.MAX_HISTORY_LEN,
            self.logger,
            self.config_manager
        )
    

    async def add_user_message(self, message: Message) -> None:
        await self._history_append_user(message)


    async def add_bot_message(self, message: Message) -> None:
        await self._history_append_bot(message)


    async def get_response(self, message: Message) -> str:
        """Get a response from the AI model for the given user message.
        The AI also considers prior conversation history in deciding its response.
        
        You should also call remember_message() with the same message first,
        to add it to the conversation history.

        Args:
            message (Message): The user message to process.

        Returns:
            str: The response from the AI model.
        """
        _prompt = await self._build_prompt(message.channel.id, message.id)
        response = await self.vllm.generate_completion(
            _prompt, 
            sampling_params = {
                "max_tokens": self.MAX_TOKENS_RESPONSE,
                "stop": self.STOP_SEQUENCES
            }
        )
        self.logger.debug("received a response: {} \n based on prompt:\n{}", response, _prompt)
        if response:
            return response['text'][0]
        else:
            return ""

    
    async def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history"""
        new_item = HistoryItem(
            timestamp = int(message.created_at.timestamp()),
            content = message.content,
            name = message.author.display_name,
            id = message.id
        )
        await self.history_manager.add_history_item(message.channel.id, new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", 
                    new_item, await self.history_manager.get_history(message.channel.id))


    async def _history_append_bot(self, message: Message) -> None:
        """Append a new AI/bot message to the conversation history"""
        new_item = HistoryItem(
            int(message.created_at.timestamp()),
            message.content,
            self.BOT_USERNAME,
            message.id
        )
        await self.history_manager.add_history_item(message.channel.id, new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}",
                            new_item, await self.history_manager.get_history(message.channel.id))


    async def _count_tokens_list(self, messages: List[HistoryItem]) -> int:
        """Count the number of prompt tokens a given list of messages will require"""
        formatted_msgs = []
        for message in messages:
            formatted_msgs.append(self._format_msg(message))
        num_tokens = await self.vllm.get_token_usage(formatted_msgs)
        return num_tokens
    

    async def _count_tokens_str(self, text: str) -> int:
        """Count the number of tokens in a string"""
        return await self.vllm.get_token_usage(text)
    

    async def _build_prompt(self, channel_id: int, reply_id: Optional[int] = None) -> str:
        """Build prompt for a new request to the LLM to generate a response
        to a given channel history. And optionally a given message id to reply to.
        
        Args: 
            channel_id: the channel id to build the prompt for
            reply_id: the message id to reply to, if any
        Returns:
            str: the prompt to use for the AI request
        """
        prompt = self.SYSTEM_MSG + self.INSTRUCTION
        if reply_id:
            prompt += f"{self.REPLY_INSTRUCTION} {reply_id}"
        prompt += "\n"
        history = await self.history_manager.get_history(channel_id)
        for message in history:
            prompt += self._format_msg(message)
        prompt += self.RESPONSE_PRIMER
        prompt += f"<messageID=TBD> {self.BOT_USERNAME}:"
        return prompt
    

    def _format_msg(self, message: HistoryItem, with_id: bool = True) -> str:
        if with_id:
            return f"<messageID={message.id}> {message.name}: {message.content}\n"
        else:
            return f"{message.name}: {message.content}\n"
        

    async def get_model_name(self) -> str:
        """Get the name of the AI model currently used by this provider.
        
        Returns:
            str: The name of the AI model.
        """
        return self.RESPONSE_MODEL