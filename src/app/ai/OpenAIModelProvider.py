from discord import Message
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
import openai


class OpenAIModelProvider(IAIModelProvider):
    """OpenAIModelProvider implementation for the OpenAI API"""


    def __init__(self, 
                 config_manager: IConfigManager,
                 logger: ILogger) -> None:
        self.logger = logger
        self.config_manager = config_manager
        openai.api_key = self.config_manager.get_parameter("OPENAI_API_KEY")
        self.RESPONSE_MODEL = self.config_manager.get_parameter("OPENAI_RESPONSE_MODEL")
        
        self.NEW_USER_MSG: dict = {"role": "user", "content": ""}
        self.NEW_AI_MSG: dict = {"role": "assistant", "content": ""}
        self.SYSTEM_MSG: dict = {"role": "system", "content": "You are pepeleli, a human-like AI-powered chatbot. Pepeleli is chill friendly and laid back by default, but moody and opinionated and can get straight up unhinged if somebody says something that pushes his buttons.  He is talking to his friends so he is honest, even vulgar at times and is fairly jaded and cynical but also has a sense of humour."}
        self.history: dict = {}


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
        self._history_append_user(message)
        channel_history = self.history.get(message.channel.id)

        response = await openai.ChatCompletion.acreate(
            model=self.RESPONSE_MODEL, 
            messages=channel_history
        )
        response_content = response['choices'][0]['message']['content']
        self.logger.debug("generated a response: {} \n based on history: {}", response_content, self.history)
        
        self._history_append_bot(response_content, message.channel.id)
        
        return response_content


    async def add_user_message(self, message: Message) -> None:
        """Add a new user message to the conversation history used by the AI,
        without requesting the AI to generate any response at this time.
        
        Args:
            message (Message): The user message to process.
        
        Returns: None
        """
        self._history_append_user(message)


    def _history_append_user(self, message: Message) -> None:
        """Append a new user message to the conversation history
        """
        new_item = self.NEW_USER_MSG.copy()
        new_item["content"] = message.content
        new_item["name"] = message.author.display_name

        self.history.setdefault(message.channel.id, []).append(new_item)
        self.logger.debug("_history_append_user is adding: {} \n new history is now: {}", new_item, self.history)


    def _history_append_bot(self, message: str, channel_id: int) -> None:
        """Append a new AI/bot message to the conversation history
        """
        new_item = self.NEW_AI_MSG.copy()
        new_item["content"] = message
        
        self.history.setdefault(channel_id, []).append(new_item)
        self.logger.debug("_history_append_bot is adding: {} \n new history is now: {}", new_item, self.history)