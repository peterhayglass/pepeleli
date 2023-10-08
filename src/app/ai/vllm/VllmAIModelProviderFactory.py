from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider
from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.vllm.VllmAIModelProvider import VllmAIModelProvider

class VllmAIModelProviderFactory(BaseAIModelProviderFactory):
    """
    Factory for creating VllmAIModelProvider
    """
    @classmethod
    def create_provider(cls, config_manager: IConfigManager, logger: ILogger) -> IAIModelProvider:
        return VllmAIModelProvider(config_manager, logger)
    
    
BaseAIModelProviderFactory.add_factory('vllm', VllmAIModelProviderFactory)