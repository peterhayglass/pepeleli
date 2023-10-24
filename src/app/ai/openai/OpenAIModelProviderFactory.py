from asyncio import AbstractEventLoop

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.openai.OpenAIModelProvider import OpenAIModelProvider
from ai.IAIModelProvider import IAIModelProvider


class OpenAIModelProviderFactory(BaseAIModelProviderFactory):    
    """
    Factory for creating OpenAIModelProvider
    """
    @classmethod
    async def create_provider(cls, config_manager: IConfigManager, logger: ILogger, event_loop: AbstractEventLoop) -> IAIModelProvider:
        return OpenAIModelProvider(config_manager, logger)


BaseAIModelProviderFactory.add_factory('openai', OpenAIModelProviderFactory)