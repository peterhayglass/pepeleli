from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Awaitable
from attr import dataclass
from decimal import Decimal

from ILogger import ILogger
from IConfigManager import IConfigManager


@dataclass
class HistoryItem:
    timestamp: Decimal
    content: str
    name: str
    id: int
    channel_id: int


class IHistoryManager(ABC):
    """Interface for the History Manager"""
    
    @abstractmethod
    def __init__(self, 
                 count_tokens: Callable[[list[HistoryItem]], Awaitable[int]], 
                 format_msg: Callable[[HistoryItem], str], 
                 max_history_len: int, 
                 logger: ILogger, 
                 config_manager: IConfigManager
                ) -> None:
        """
        Args:
            count_tokens: reference to an async coroutine that counts tokens in a given list of history items.
                        happens outside the history manager so that a model-appropriate tokenizer can be used,
                        and model-appropriate prompt formatting can be used, e.g. EOS tokens.

            format_msg: reference to a function that formats a given history item for inclusion in the prompt,
                        i.e. including username, message id, etc
                        used in managing history length to stay within context length.

            context_len: the maximum number of tokens that can be expected to fit within context,
                        used in managing history length to stay within context length.

            logger: reference to the active logger instance

            config_manager: reference to the active config manager instance
        """
        pass


    @abstractmethod
    async def get_history(self, channel_id: int) -> deque[HistoryItem]:
        """Retrieve the history for a given channel ID"""
        pass


    @abstractmethod
    async def add_history_item(self, channel_id: int, item: HistoryItem) -> None:
        """Add an item to the history for a given channel ID"""
        pass


    @abstractmethod
    async def clear_history(self, channel_id: int) -> None:
        """Clear the history for a given channel ID"""
        pass



