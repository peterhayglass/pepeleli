from collections import deque
from discord import Message
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
import openai
import tiktoken


class OpenAIModelProvider(IAIModelProvider):
    """OpenAIModelProvider implementation for the OpenAI API"""


    def __init__(self, 
                 config_manager: IConfigManager,
                 logger: ILogger) -> None:
        self.logger = logger
        self.config_manager = config_manager
        
        try:
            openai.api_key = self.config_manager.get_parameter("OPENAI_API_KEY")
            self.RESPONSE_MODEL = self.config_manager.get_parameter("OPENAI_RESPONSE_MODEL")
            self.MAX_CONTEXT_LEN = int(self.config_manager.get_parameter("OPENAI_MAX_CONTEXT_LEN"))
        except ValueError as ve:
            self.logger.exception("error loading OpenAIModelProvider configuration: ", ve)
            raise
        
        self.NEW_USER_MSG: dict = {"role": "user", "content": ""}
        self.NEW_AI_MSG: dict = {"role": "assistant", "content": ""}
        self.SYSTEM_MSG: dict = {"role": "system", "content": "You are pepeleli, a human-like AI-powered chatbot. Pepeleli is chill friendly and laid back by default, but moody and opinionated and can get straight up unhinged if somebody says something that pushes his buttons.  He is talking to his friends so he is honest, even vulgar at times and is fairly jaded and cynical but also has a sense of humour."}
        
        self.TOKEN_ENCODING_TYPE = "cl100k_base"
        self.MAX_TOKENS_RESPONSE = 200
        
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

        response = await openai.ChatCompletion.acreate(
            model=self.RESPONSE_MODEL, 
            messages=list(channel_history),
            max_tokens=self.MAX_TOKENS_RESPONSE
        )
        response_content = response['choices'][0]['message']['content']
        self.logger.debug("generated a response: {} \n based on history: {}", response_content, self.history)
        
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


    async def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history
        """
        new_item = self.NEW_USER_MSG.copy()
        new_item["content"] = message.content
        new_item["name"] = message.author.display_name

        self.history.setdefault(message.channel.id, deque()).append(new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", new_item, self.history)


    async def _history_append_bot(self, message: str, channel_id: int) -> None:
        """Append a new AI/bot message to the conversation history
        """
        new_item = self.NEW_AI_MSG.copy()
        new_item["content"] = message
        
        self.history.setdefault(channel_id, deque()).append(new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}", new_item, self.history)


    async def _check_history_len(self, channel_id: int) -> None:
        """Check if the history length has become too long,
        truncate if necessary
        """
        channel_history = self.history.get(channel_id, deque())
        total_len = sum(
            self._count_tokens(d["content"]) for d in channel_history
            )
        self.logger.debug(
            f"_check_history_len found length {total_len} for channel {channel_id}")
        
        while (total_len + self.MAX_TOKENS_RESPONSE) > self.MAX_CONTEXT_LEN and channel_history:
            #TODO: archive history in a retrieveable manner
            #for now: just truncate it.
            removed = channel_history.popleft()
            len_diff = self._count_tokens(removed["content"])
            total_len -= len_diff
            self.logger.debug(
                f"_check_history_len truncated {len_diff} tokens "
                f"for a new total length of {total_len}")
        
        self.history[channel_id] = channel_history
    
        
    def _count_tokens(self, string: str) -> int:
        """Count the number of tokens a given string will be tokenized to
        """
        encoding = tiktoken.get_encoding(self.TOKEN_ENCODING_TYPE)
        return len(encoding.encode(string))