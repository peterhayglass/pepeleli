from ai.BaseAIModelProviderFactory import BaseAIModelProviderFactory
from ai.OobaAIModelProvider import OobaAIModelProvider
from IConfigManager import IConfigManager
from ILogger import ILogger


class OobaAIModelProviderFactory(BaseAIModelProviderFactory):
    @classmethod
    def create_provider(cls, config_manager: IConfigManager, logger: ILogger) -> OobaAIModelProvider:
        return OobaAIModelProvider(config_manager, logger)


BaseAIModelProviderFactory.add_factory('ooba', OobaAIModelProviderFactory)