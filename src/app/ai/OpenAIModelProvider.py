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
        
        self.NEW_USER_MSG: dict = {"role": "user", "content": ""}
        self.NEW_AI_MSG: dict = {"role": "assistant", "content": ""}
        self.SYSTEM_MSG: dict = {"role": "system", "content": "You are pepeleli, a human-like AI-powered chatbot. Pepeleli is chill friendly and laid back by default, but moody and opinionated and can get straight up unhinged if somebody says something that pushes his buttons.  He is talking to his friends so he is honest, even vulgar at times and is fairly jaded and cynical but also has a sense of humour."}
        self.history: dict = {}


    async def get_response(self, message: Message) -> str:
        user_history = self.history.get(message.author.id)
        if not user_history:
            user_history = [self.NEW_USER_MSG.copy()]
            user_history[0]["content"] = message.content
        else:
            new_item = self.NEW_USER_MSG.copy()
            new_item["content"] = message.content
            user_history.append(new_item)

        response = await openai.ChatCompletion.acreate(
            model="gpt-4", 
            messages=user_history
        )
        response_content = response['choices'][0]['message']['content']
        new_item = self.NEW_AI_MSG.copy()
        new_item["content"] = response_content
        user_history.append(new_item)
        self.history[message.author.id] = user_history
        return response_content