import json
from collections import deque
from typing import Optional
from decimal import Decimal

from discord import Message
import openai
import tiktoken

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
from IHistoryManager import IHistoryManager, HistoryItem
from HistoryManager import HistoryManager


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
            openai.api_base = self.config_manager.get_parameter("OPENAI_INSTRUCT_PROVIDER_BASE_URI")
            self.RESPONSE_MODEL = self.config_manager.get_parameter("OPENAI_INSTRUCT_RESPONSE_MODEL")
            self.MAX_CONTEXT_LEN = int(self.config_manager.get_parameter("OPENAI_MAX_CONTEXT_LEN"))
            self.BOT_USERNAME = self.config_manager.get_parameter("BOT_USERNAME")
            self.STOP_SEQUENCES: list[str] = json.loads(self.config_manager.get_parameter("STOP_SEQUENCES"))
            self.MODERATION_THRESHOLD = float(self.config_manager.get_parameter("OPENAI_MODERATION_THRESHOLD"))
        except ValueError as ve:
            self.logger.exception("error loading OpenAIModelProvider configuration: ", ve)
            raise
        
        self.SYSTEM_MSG = f"""### Begin system message:
### character info: {self.BOT_USERNAME} is an eccentric character, chill, friendly and laid back by default, but moody and opinionated and not shy about sharing opinions.  {self.BOT_USERNAME} can even get straight up unhinged if somebody says something that pushes his buttons, is fairly jaded and cynical in general but also has a sense of humour.  He is talking to his friends so he is honest, even a bit vulgar at times.  Despite the rough edges, {self.BOT_USERNAME} has a good heart.
### End system message\n"""

        self.INSTRUCTION = f"### Instruction: continue the chat dialogue below by writing only a single reply in character as {self.BOT_USERNAME}. Do not write messages for other users. Do not write narration, system messages or anything other than dialogue from {self.BOT_USERNAME}."
        self.REPLY_INSTRUCTION = f" Do not mention message ID numbers or specifically say you are replying, however do consider that {self.BOT_USERNAME} is replying to messageID:"
        self.MENTAL_HEALTH_MSG = """\nPlease don't harm yourself.
Consider checking out these links to find someone to talk to:  
    <https://findahelpline.com/i/iasp>
    <https://befrienders.org/> 
    <https://www.samaritans.org/> """
        self.TOKEN_ENCODING_TYPE = "cl100k_base"
        self.MAX_TOKENS_RESPONSE = 250
        self.IGNORE_EMOJI = '❌'

        self.MAX_HISTORY_LEN = self.MAX_CONTEXT_LEN - (
            self._count_tokens_str(self.SYSTEM_MSG) 
            + self._count_tokens_str(self.INSTRUCTION)
            + self._count_tokens_str(self.REPLY_INSTRUCTION)
            + self.MAX_TOKENS_RESPONSE
        )
        self.history_manager: IHistoryManager = HistoryManager(
            self._count_tokens_list,
            self._format_msg,
            self.MAX_HISTORY_LEN,
            self.logger,
            self.config_manager
        )



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
        
        moderate_reasons = await self._get_moderation(message.content, message.channel.id)
        if moderate_reasons:
            if any(reason in moderate_reasons for reason in 
            ["self-harm", "self-harm/intent", "self-harm/instructions"]):
                reason_msg = self.MENTAL_HEALTH_MSG
            else:
                reason_msg = (f"`your message has been blocked by content moderation and will be ignored. \n"
                f"reason: {moderate_reasons}`")
                await message.add_reaction(self.IGNORE_EMOJI)
            await message.channel.send(reason_msg, reference=message)
            return ""
        
        
        _prompt = await self._build_prompt(message.channel.id, message.id)
        response = openai.Completion.create(
            model=self.RESPONSE_MODEL,
            prompt=_prompt,
            max_tokens=self.MAX_TOKENS_RESPONSE,
            stop=self.STOP_SEQUENCES
        )
        response_content = response['choices'][0]['text']
        self.logger.debug("received a response: {} \n based on prompt:\n{}", response, _prompt)
        
        moderate_reasons = await self._get_moderation(response_content, message.channel.id)
        if moderate_reasons:
            return ("`the AI-generated response to your message has been blocked "
                f"by content moderation and will not be shown. \nreason: {moderate_reasons}`"
            )
        else:          
            return response_content


    async def add_user_message(self, message: Message) -> None:
        """Add a new user message to the conversation history used by the AI,
        without requesting the AI to generate any response at this time.
        
        Args:
            message (Message): The user message to process.
        
        Returns: None
        """
        moderate_reasons = await self._get_moderation(message.content, message.channel.id)
        if moderate_reasons:
            self.logger.warning(f"ignoring a message {message.id} due to content moderation. \n"
                f"reasons: {moderate_reasons} \n message content: {message.content}")
            if not any(reason in moderate_reasons for reason in 
            ["self-harm", "self-harm/intent", "self-harm/instructions"]):
                await message.add_reaction(self.IGNORE_EMOJI)
            return
        
        await self._history_append_user(message)


    async def add_bot_message(self, message: Message) -> None:
        await self._history_append_bot(message)


    async def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history
        """
        new_item = HistoryItem(
            timestamp = Decimal(message.created_at.timestamp()),
            content = message.content,
            name = message.author.display_name,
            id = message.id,
            channel_id = message.channel.id
        )
        await self.history_manager.add_history_item(message.channel.id, new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", 
                            new_item, await self.history_manager.get_history(message.channel.id))


    async def _history_append_bot(self, message: Message) -> None:
        """Append a new AI/bot message to the conversation history
        """
        new_item = HistoryItem(
            timestamp = Decimal(message.created_at.timestamp()),
            content = message.content,
            name = self.BOT_USERNAME,
            id = message.id,
            channel_id = message.channel.id
        )
        await self.history_manager.add_history_item(message.channel.id, new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}",
                            new_item, await self.history_manager.get_history(message.channel.id))
    
        
    async def _count_tokens_list(self, messages: list[HistoryItem]) -> int:
        """Count the number of prompt tokens a given list of messages will require"""
        num_tokens = 0
        for message in messages:
            formatted_msg = self._format_msg(message)
            num_tokens += self._count_tokens_str(formatted_msg)
        return num_tokens

    
    def _count_tokens_str(self, text: str) -> int:
        """Count the number of tokens in a given string"""
        encoding = tiktoken.get_encoding(self.TOKEN_ENCODING_TYPE)
        return len(encoding.encode(text))


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
        prompt += f"<messageID=TBD> {self.BOT_USERNAME}:"
        return prompt


    def _format_msg(self, message: HistoryItem, with_id: bool = True) -> str:
        if with_id:
            return f"<messageID={message.id}> {message.name}: {message.content}\n"
        else:
            return f"{message.name}: {message.content}\n"


    async def _get_moderation(self, text: str, channel_id: int) -> Optional[list[str]]:
        """Classify the given text via openAI moderations endpoint, to determine
        if openAI content policy is potentially being violated.
        Attempts to include recent conversation history from the same channel,
        to make a context-aware moderation decision.

        Args: 
            text (string) : the new message text to classify.
            channel_id (int) : id for a channel to include history from,
                for context-aware moderation.

        Returns: a list of strings with the reason(s) to moderate this content,
                 or None if the content is acceptable
        """
        if not self.MODERATION_THRESHOLD:
            return None
        
        history = await self.history_manager.get_history(channel_id)
        context = list(history)[-4:]
        
        messages = []
        for msg in context:
            messages.append(self._format_msg(msg, with_id=False))
        messages.append(f"{text}")
        msg_with_context = "".join(messages)

        response = await openai.Moderation.acreate(input=msg_with_context, model='text-moderation-latest')
        
        moderation = response["results"][0]
        self.logger.debug("got moderation {} \n for: {}", moderation, msg_with_context)
        if not moderation["flagged"]:
            return None
        
        categories = moderation["categories"]
        scores = moderation["category_scores"]
        reasons = []
        log_reasons = []
        for reason, moderate in categories.items():
            if moderate and (scores[reason] > self.MODERATION_THRESHOLD):
                reasons.append(reason)
                log_reasons.append(f"{reason}: {scores[reason]}")
        
        self.logger.warning(f"moderation matched categories {log_reasons}\n"
            f"for the text: {msg_with_context}")

        return reasons
    

    async def get_model_name(self) -> str:
        """Get the name of the AI model currently used by this provider.
        
        Returns:
            str: The name of the AI model.
        """
        return self.RESPONSE_MODEL