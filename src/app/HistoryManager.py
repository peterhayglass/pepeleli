from collections import deque
from typing import Callable, Awaitable, List, Union

import aioboto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

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
        self.count_tokens = count_tokens
        self.format_msg = format_msg
        self.max_history_len = max_history_len
        self.logger = logger
        self.config_manager = config_manager
        self._session = aioboto3.Session(region_name='us-west-2')
        
        self._local_history: dict[int, deque[HistoryItem]] = {} #in-memory message history, keyed by channel id
        
    
    async def get_history(self, channel_id: int) -> deque[HistoryItem]:
        """Retrieve the history for a given channel ID,
        from in-memory cache if available, otherwise from dynamodb"""
        if channel_id not in self._local_history:
            self._local_history[channel_id] = await self._get_persisted_history(channel_id)
        return self._local_history[channel_id]


    async def _get_persisted_history(self, channel_id: int) -> deque[HistoryItem]:
        """Retrieve persisted history for a given channel ID from dynamodb"""
        
        async with self._session.resource('dynamodb') as dynamodb:
            table = await dynamodb.Table('pepeleli-chat-history')
            response = await table.query(
                KeyConditionExpression=Key('channel_id').eq(channel_id),
                ScanIndexForward=True
            )
            if 'Items' in response:
                history_items = [HistoryItem(**item) for item in response['Items']] #type: ignore
                return deque(history_items)
            else:
                return deque()


    async def add_history_item(self, channel_id: int, item: HistoryItem) -> None:
        """Add an item to the history for a given channel ID"""
        channel_history = await self.get_history(channel_id)
        channel_history.append(item)
        self._local_history[channel_id] = channel_history
        await self._persist_history_item(item)
        await self._trim_history(channel_id)


    async def _persist_history_item(self, item: HistoryItem) -> None:
        """Persist a history item to dynamodb for a given channel ID"""
        async with self._session.resource('dynamodb') as dynamodb:
            table = await dynamodb.Table('pepeleli-chat-history')
            try:
                await table.put_item(
                    Item = item.__dict__,
                    ConditionExpression="attribute_not_exists(message_id)"
                )
            except ClientError as ce:
                if ce.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    self.logger.error(
                        f"persist_history_item failed: a message with the given ID {item.id} already exists")
                else:
                    raise


    async def clear_history(self, channel_id: int) -> None:
        """Clear the history for a given channel ID"""
        self._local_history[channel_id] = deque()


    async def _trim_history(self, channel_id: int) -> None:
        """Trim the history for a given channel ID to stay within context length.
        Currently just truncates, will eventually archive
        """
        channel_history = await self.get_history(channel_id)
        history_len = await self.count_tokens(list(channel_history))
        self.logger.debug(
            f"_trim_history found history length {history_len} for channel {channel_id}")
        
        all_removed: List[HistoryItem] = []
        while history_len > self.max_history_len and channel_history:
            #TODO: archive history in a retrieveable manner
            #for now: just truncate it.
            removed = channel_history.popleft()
            all_removed.append(removed)
            len_diff = await self.count_tokens([removed])
            history_len -= len_diff
            self.logger.debug(
                f"_trim_history truncated {len_diff} tokens "
                f"for a new total length of {history_len}")
            
        if all_removed:
            await self._delete_persisted_items(all_removed)
        self._local_history[channel_id] = channel_history


    async def _delete_persisted_items(self, items: Union[HistoryItem, List[HistoryItem]]) -> None:
        """Delete the given history item(s) from dynamodb.
        items must all have the same channel_id"""
        if not isinstance(items, list):
            items = [items]
        
        channel_id = items[0].channel_id

        async with self._session.resource("dynamodb") as dynamodb:
            table = await dynamodb.Table("your_chat_history_table")

            response = await table.query(
                KeyConditionExpression=(
                    Key("channel_id").eq(channel_id)
                )
            )
            message_timestamps = {item['message_id']: item['timestamp'] 
                                  for item in response['Items'] if item['message_id'] in items}

            async with table.batch_writer() as batch:
                for message_id in items:
                    if message_id in message_timestamps:
                        await batch.delete_item(Key={"channel_id": channel_id, "timestamp": message_timestamps[message_id]}) #type:ignore
                        self.logger.debug(f"HistoryItem with message_id '{message_id}' has been deleted in channel {channel_id}")

                    else:
                        self.logger.debug(f"No HistoryItem with message_id '{message_id}' found in channel {channel_id}")