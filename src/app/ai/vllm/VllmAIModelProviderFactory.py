from asyncio import AbstractEventLoop

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
    async def create_provider(cls, 
                        config_manager: IConfigManager, 
                        logger: ILogger, 
                        event_loop: AbstractEventLoop
                        ) -> IAIModelProvider:
        vllm = VllmAIModelProvider(config_manager, logger)
        await vllm._init_async()
        return vllm
    
    
BaseAIModelProviderFactory.add_factory('vllm', VllmAIModelProviderFactory)