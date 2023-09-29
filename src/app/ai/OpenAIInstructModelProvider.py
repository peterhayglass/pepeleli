from collections import deque
from discord import Message
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
import openai
import tiktoken


class OpenAIInstructModelProvider(IAIModelProvider):
    """OpenAIModelProvider implementation for the OpenAI API completions endpoint
    intended for gpt-3.5-turbo-instruct
    """


    def __init__(self, 
                 config_manager: IConfigManager,
                 logger: ILogger) -> None:
        self.logger = logger
        self.config_manager = config_manager
        
        try:
            openai.api_key = self.config_manager.get_parameter("OPENAI_API_KEY")
            self.RESPONSE_MODEL = self.config_manager.get_parameter("OPENAI_INSTRUCT_RESPONSE_MODEL")
            self.MAX_CONTEXT_LEN = int(self.config_manager.get_parameter("OPENAI_MAX_CONTEXT_LEN"))
            self.BOT_USERNAME = self.config_manager.get_parameter("BOT_USERNAME")
        except ValueError as ve:
            self.logger.exception("error loading OpenAIModelProvider configuration: ", ve)
            raise
        
        self.SYSTEM_MSG = f"""### Begin system message:
### character info: {self.BOT_USERNAME} is an eccentric character, chill, friendly and laid back by default, but moody and opinionated and not shy about sharing opinions.  {self.BOT_USERNAME} can even get straight up unhinged if somebody says something that pushes his buttons, is fairly jaded and cynical in general but also has a sense of humour.  He is talking to his friends so he is honest, even a bit vulgar at times.  Despite the rough edges, {self.BOT_USERNAME} has a good heart.
### End system message\n"""

        self.INSTRUCTION = f"### Instruction: continue the chat dialogue below by writing a reply in character as {self.BOT_USERNAME}.\n"
        self.TOKEN_ENCODING_TYPE = "cl100k_base"
        self.MAX_TOKENS_RESPONSE = 1000

        self.MAX_HISTORY_LEN = self.MAX_CONTEXT_LEN - (
            self._count_tokens_str(self.SYSTEM_MSG) 
            + self._count_tokens_str(self.INSTRUCTION)
            + self.MAX_TOKENS_RESPONSE
        )

        self.history: dict[int, deque] = {} #per-channel message history, keyed by channel id


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
        while self._count_tokens_str(_prompt) > self.MAX_CONTEXT_LEN:
            channel_history.popleft()
            _prompt = await self._build_prompt(message.channel.id)

        self.history[message.channel.id] = channel_history

        response = openai.Completion.create(
            model=self.RESPONSE_MODEL,
            prompt=_prompt,
            max_tokens=self.MAX_TOKENS_RESPONSE
        )
        response_content = response['choices'][0]['text']
        self.logger.debug("generated a response: {} \n based on prompt:\n{}", response_content, _prompt)
        
        await self._history_append_bot(response_content, message.channel.id)
        
        return response_content


    async def add_user_message(self, message: Message) -> None:
        """Add a new user message to the conversation history used by the AI,
        without requesting the AI to generate any response at this time.
        
        Args:
            message (Message): The user message to process.
        
        Returns: None
        """
        await self._history_append_user(message)
        await self._check_history_len(message.channel.id)


    async def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history
        """
        new_item = {}
        new_item["content"] = message.content
        new_item["name"] = message.author.display_name

        self.history.setdefault(message.channel.id, deque()).append(new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", new_item, self.history)


    async def _history_append_bot(self, message: str, channel_id: int) -> None:
        """Append a new AI/bot message to the conversation history
        """
        new_item = {}
        new_item["content"] = message
        new_item["name"] = self.BOT_USERNAME
        
        self.history.setdefault(channel_id, deque()).append(new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}", new_item, self.history)


    async def _check_history_len(self, channel_id: int) -> None:
        """Check if the history length has become too long for the context window,
        truncate if necessary.  
        """
        channel_history = self.history.get(channel_id, deque())
        history_len = await self._count_tokens_list(list(channel_history))
        self.logger.debug(
            f"_check_history_len found history length {history_len} for channel {channel_id}")
        
        while history_len > self.MAX_HISTORY_LEN and channel_history:
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
        num_tokens = 0
        for message in messages:
            formatted_msg = f"{message.get('name')}: {message.get('content')}\n"
            num_tokens += self._count_tokens_str(formatted_msg)
        return num_tokens

    
    def _count_tokens_str(self, text: str) -> int:
        """Count the number of tokens in a given string"""
        encoding = tiktoken.get_encoding(self.TOKEN_ENCODING_TYPE)
        return len(encoding.encode(text))


    async def _build_prompt(self, channel_id: int) -> str:
        """Build prompt for a new request to the LLM,
        for a given channel history"""
        prompt = self.SYSTEM_MSG + self.INSTRUCTION
        history = self.history.get(channel_id, deque())
        for message in history:
            prompt += f"{message.get('name')}: {message.get('content')}\n"
        prompt += f"{self.BOT_USERNAME}:"
        return prompt
