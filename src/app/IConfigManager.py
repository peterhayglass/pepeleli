from abc import ABC, abstractmethod

class IConfigManager(ABC):
    """Interface for the Configuration Manager"""

    @abstractmethod
    def get_bot_token(self) -> str:
        """Retrieve bot token"""
        pass
