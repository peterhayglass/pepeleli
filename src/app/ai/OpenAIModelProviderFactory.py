from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.OpenAIModelProvider import OpenAIModelProvider
from ai.IAIModelProvider import IAIModelProvider


class OpenAIModelProviderFactory(BaseAIModelProviderFactory):    
    """
    Factory for creating OpenAIModelProvider
    """
    @classmethod
    def create_provider(cls, config_manager: IConfigManager, logger: ILogger) -> IAIModelProvider:
        return OpenAIModelProvider(config_manager, logger)


BaseAIModelProviderFactory.add_factory('openai', OpenAIModelProviderFactory)