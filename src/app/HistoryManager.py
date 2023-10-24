from collections import deque
from typing import Callable, Awaitable, List

from ILogger import ILogger
from IConfigManager import IConfigManager
from IHistoryManager import IHistoryManager, HistoryItem


class HistoryManager(IHistoryManager):
    def __init__(self, 
                 count_tokens: Callable[[List[HistoryItem]], Awaitable[int]], 
                 format_msg: Callable[[HistoryItem], str], 
                 max_history_len: int, 
                 logger: ILogger, 
                 config_manager: IConfigManager
                ) -> None:
        """
        Args:
            count_tokens: reference to a method that counts tokens in a given list of history items.
                        happens outside the history manager so that a model-appropriate tokenizer can be used,
                        and model-appropriate prompt formatting can be used, e.g. EOS tokens.

            format_msg: reference to a method that formats a given history item for inclusion in the prompt,
                        i.e. including username, message id, etc
                        used in managing history length to stay within context length.

            context_len: the maximum number of tokens that can be expected to fit within context,
                        used in managing history length to stay within context length.

            logger: reference to the active logger instance

            config_manager: reference to the active config manager instance
        """
        self.count_tokens = count_tokens
        self.format_msg = format_msg
        self.max_history_len = max_history_len
        self.logger = logger
        self.config_manager = config_manager
        
        self._local_history: dict[int, deque[HistoryItem]] = {} #in-memory message history, keyed by channel id
        #TODO: load persisted history from db
        
    
    async def get_history(self, channel_id: int) -> deque[HistoryItem]:
        """Retrieve the history for a given channel ID"""
        return self._local_history.get(channel_id, deque())


    async def add_history_item(self, channel_id: int, item: HistoryItem) -> None:
        """Add an item to the history for a given channel ID"""
        try:
            new_item = HistoryItem(
                timestamp=item.timestamp,
                content=item.content,
                name=item.name,
                id=item.id
            )
        except AttributeError as ae:
            self.logger.exception(
                "add_history_item received an invalid HistoryItem object", ae)
            raise
        
        channel_history = self._local_history.get(channel_id, deque())
        channel_history.append(new_item)
        self._local_history[channel_id] = channel_history
        await self._trim_history(channel_id)


    async def clear_history(self, channel_id: int) -> None:
        """Clear the history for a given channel ID"""
        self._local_history[channel_id] = deque()


    async def _trim_history(self, channel_id: int) -> None:
        """Trim the history for a given channel ID to stay within context length.
        Currently just truncates, will eventually archive
        """
        channel_history = self._local_history.get(channel_id, deque())
        history_len = await self.count_tokens(list(channel_history))
        self.logger.debug(
            f"_trim_history found history length {history_len} for channel {channel_id}")
        
        while history_len > self.max_history_len and channel_history:
            #TODO: archive history in a retrieveable manner
            #for now: just truncate it.
            removed = channel_history.popleft()
            len_diff = await self.count_tokens([removed])
            history_len -= len_diff
            self.logger.debug(
                f"_trim_history truncated {len_diff} tokens "
                f"for a new total length of {history_len}")
        
        self._local_history[channel_id] = channel_history