from collections import deque
from functools import cached_property
import json

from discord import Message

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
from ai.vllm.VLLMClient import VLLMClient


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
        except ValueError as ve:
            self.logger.exception("error loading VLLMAIModelProvider configuration: ", ve)
            raise

        self.SYSTEM_MSG = f"""### Begin system message:
### character info: {self.BOT_USERNAME} is an eccentric character, chill, friendly and laid back by default, but moody and opinionated and not shy about sharing opinions.  {self.BOT_USERNAME} can even get straight up unhinged if somebody says something that pushes his buttons, is fairly jaded and cynical in general but also has a sense of humour.  He is talking to his friends so he is honest, even a bit vulgar at times.  Despite the rough edges, {self.BOT_USERNAME} has a good heart.
### End system message\n"""
        self.INSTRUCTION = f"### Instruction: continue the chat dialogue below by writing only a single reply in character as {self.BOT_USERNAME}. Do not write messages for other users.\n"
        self.MAX_TOKENS_RESPONSE = 250
        self.IGNORE_EMOJI = '❌'
        
        self.history: dict[int, deque] = {} #per-channel message history, keyed by channel id
        self.vllm = VLLMClient(_host, _port)
        self._max_history_len: int = 0


    @property
    async def MAX_HISTORY_LEN(self) -> int:
        if not self._max_history_len:
            self._max_history_len = self.MAX_CONTEXT_LEN - (
                await self._count_tokens_str(self.SYSTEM_MSG)
                + await self._count_tokens_str(self.INSTRUCTION)
                + self.MAX_TOKENS_RESPONSE
            )
        return self._max_history_len
    

    async def add_user_message(self, message: Message) -> None:
        await self._history_append_user(message)
        await self._check_history_len(message.channel.id)


    async def add_bot_message(self, message: Message) -> None:
        await self._history_append_bot(message)
        await self._check_history_len(message.channel.id)


    async def get_response(self, message: Message) -> str:
        """Get a response from the AI model for the given user message.
        The AI also considers prior conversation history in deciding its response.
        
        The user message passed to get_response() is automatically added to history,
        so do not call add_user_message() separately for the same message.

        Args:
            message (Message): The user message to process.

        Returns:
            str: The response from the AI model.
        """
        await self._history_append_user(message)
        await self._check_history_len(message.channel.id)
        channel_history = self.history.get(message.channel.id, deque())

        _prompt = await self._build_prompt(message.channel.id)
        _prompt_len = await self._count_tokens_str(_prompt)
        _potential_len = _prompt_len + self.MAX_TOKENS_RESPONSE
        while _prompt_len > self.MAX_CONTEXT_LEN:
            self.logger.debug(f"detected excessive prompt length {_prompt_len} at prompt generation, "
                              f"potential total length {_potential_len}, truncating")
            channel_history.popleft()
            _prompt = await self._build_prompt(message.channel.id)
            _prompt_len = await self._count_tokens_str(_prompt)
            _potential_len = _prompt_len + self.MAX_TOKENS_RESPONSE

        self.logger.debug(f"final prompt length for request is {_prompt_len}")
        self.history[message.channel.id] = channel_history

        response = await self.vllm.generate_completion(
            _prompt, 
            sampling_params = {
                "max_tokens": self.MAX_TOKENS_RESPONSE,
                "stop": self.STOP_SEQUENCES
            }
        )
        if response:
            return response['text'][0]
        else:
            return ""


    async def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history
        """
        new_item: dict = {}
        new_item["content"] = message.content
        new_item["name"] = message.author.display_name
        new_item["id"] = message.id

        self.history.setdefault(message.channel.id, deque()).append(new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", new_item, self.history)


    async def _history_append_bot(self, message: Message) -> None:
        """Append a new AI/bot message to the conversation history
        """
        new_item: dict = {}
        new_item["content"] = message.content
        new_item["name"] = self.BOT_USERNAME
        new_item["id"] = message.id
        
        self.history.setdefault(message.channel.id, deque()).append(new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}", new_item, self.history)


    async def _check_history_len(self, channel_id: int) -> None:
        """Check if the history length has become too long for the context window,
        truncate if necessary.  
        """
        channel_history = self.history.get(channel_id, deque())
        history_len = await self._count_tokens_list(list(channel_history))
        self.logger.debug(
            f"_check_history_len found history length {history_len} for channel {channel_id}")
        
        while history_len > await self.MAX_HISTORY_LEN and channel_history:
            #TODO: archive history in a retrieveable manner
            #for now: just truncate it.
            removed = channel_history.popleft()
            len_diff = await self._count_tokens_list([removed])
            history_len -= len_diff
            self.logger.debug(
                f"_check_history_len truncated {len_diff} tokens "
                f"for a new total length of {history_len}")
        
        self.history[channel_id] = channel_history


    async def _count_tokens_list(self, messages: list) -> int:
        """Count the number of prompt tokens a given list of messages will require"""
        formatted_msgs = []
        for message in messages:
            formatted_msgs.append(self._format_msg(message))
        num_tokens = await self.vllm.get_token_usage(formatted_msgs)
        return num_tokens
    

    async def _count_tokens_str(self, text: str) -> int:
        """Count the number of tokens in a string"""
        return await self.vllm.get_token_usage(text)
    

    async def _build_prompt(self, channel_id: int) -> str:
        """Build prompt for a new request to the LLM,
        for a given channel history"""
        prompt = self.SYSTEM_MSG + self.INSTRUCTION
        history = self.history.get(channel_id, deque())
        for message in history:
            prompt += self._format_msg(message)
        prompt += f"<messageID=TBD> {self.BOT_USERNAME}:"
        return prompt
    

    def _format_msg(self, message: dict, with_id: bool = True) -> str:
        if with_id:
            return f"<messageID={message.get('id')}> {message.get('name')}: {message.get('content')}\n"
        else:
            return f"{message.get('name')}: {message.get('content')}\n"
        

    async def get_model_name(self) -> str:
        """Get the name of the AI model currently used by this provider.
        
        Returns:
            str: The name of the AI model.
        """
        return self.RESPONSE_MODEL