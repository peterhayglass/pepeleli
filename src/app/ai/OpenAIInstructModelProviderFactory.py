import imp
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.OpenAIInstructModelProvider import OpenAIInstructModelProvider
from ai.IAIModelProvider import IAIModelProvider


class OpenAIInstructModelProviderFactory(BaseAIModelProviderFactory):    
    """
    Factory for creating OpenAIInstructModelProvider
    """
    @classmethod
    def create_provider(cls, config_manager: IConfigManager, logger: ILogger) -> IAIModelProvider:
        return OpenAIInstructModelProvider(config_manager, logger)


BaseAIModelProviderFactory.add_factory('openai-instruct', OpenAIInstructModelProviderFactory)