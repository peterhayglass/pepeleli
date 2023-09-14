from abc import ABC, abstractmethod


class IConfigManager(ABC):
    """Interface for the Configuration Manager"""
   
    @abstractmethod
    def get_parameter(self, key: str) -> str:
        """Retrieve a configuration parameter"""
        pass