from asyncio import AbstractEventLoop

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.openai.OpenAIInstructModelProvider import OpenAIInstructModelProvider
from ai.IAIModelProvider import IAIModelProvider


class OpenAIInstructModelProviderFactory(BaseAIModelProviderFactory):    
    """
    Factory for creating OpenAIInstructModelProvider
    """
    @classmethod
    async def create_provider(cls, 
                        config_manager: IConfigManager, 
                        logger: ILogger, 
                        event_loop: AbstractEventLoop
                        ) -> IAIModelProvider:
        return OpenAIInstructModelProvider(config_manager, logger)


BaseAIModelProviderFactory.add_factory('openai-instruct', OpenAIInstructModelProviderFactory)