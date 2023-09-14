from abc import ABC, abstractmethod
from typing import Type
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.IAIModelProvider import IAIModelProvider


class BaseAIModelProviderFactory(ABC):
    """Base AI Model Provider Factory."""
    _factories: dict = {}


    @classmethod
    def add_factory(cls, key: str, factory: Type['BaseAIModelProviderFactory']) -> None:
        """Method for adding a factory to dictionary"""
        cls._factories[key] = factory


    @classmethod
    @abstractmethod
    def create_provider(cls, config_manager: IConfigManager, logger: ILogger) -> IAIModelProvider:
        """Create method to be implemented in subclass"""
        pass


    @classmethod
    def create(cls, key: str, config_manager: IConfigManager, logger: ILogger) -> IAIModelProvider:
        """Method for creating an instance of AIModelProvider"""
        factory = cls._factories.get(key)
        if not factory:
            raise ValueError(f"No provider available for key: {key}")
        return factory.create_provider(config_manager, logger)