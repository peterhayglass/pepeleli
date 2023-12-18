import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from collections import deque
from datetime import datetime
from decimal import Decimal

from IConfigManager import IConfigManager
from ILogger import ILogger
from HistoryManager import HistoryManager, HistoryItem

"""
these tests are pretty incomplete
TODO: figure out mocking for aioboto3 to test the rest of HistoryManager
"""

@pytest.fixture
def config_manager_history() -> IConfigManager:
    config_manager_history = MagicMock(spec=IConfigManager)
    fake_params = {
        "AWS_ACCESS_KEY_ID": "fake_access_key",
        "AWS_SECRET_ACCESS_KEY": "fake_secret_key",
        "AWS_DYNAMODB_TABLE_NAME": "pepeleli-chat-history",
        "PERSIST_HISTORY": "true"
    }
    config_manager_history.get_parameter.side_effect = lambda param_name: fake_params[param_name]

    return config_manager_history


@pytest.fixture
def history_manager(logger: ILogger, config_manager_history: IConfigManager) -> HistoryManager:
    count_tokens = AsyncMock(return_value=10)
    format_msg = lambda h_item: f"{h_item.id}: {h_item.name} - {h_item.content}"

    history_manager = HistoryManager(count_tokens, format_msg, 4096, logger, config_manager_history)
    return history_manager


@pytest.fixture
def logger() -> ILogger:
    return MagicMock(spec=ILogger)


@pytest.fixture
def sample_history_item() -> HistoryItem:
    return HistoryItem(
        timestamp=Decimal(datetime.now().timestamp()),
        content="Test message",
        name="User",
        id=1234,
        channel_id=1
    )


def test_get_history_local_present(history_manager: HistoryManager, sample_history_item: HistoryItem) -> None:
    
    history_manager._local_history = {1: deque([sample_history_item])}

    async def run_test() -> None:
        history = await history_manager.get_history(1)
        assert history == deque([sample_history_item])

    asyncio.run(run_test())


def test_clear_history(history_manager: HistoryManager, sample_history_item: HistoryItem) -> None:

    history_manager._local_history = {1: deque([sample_history_item])}

    async def run_test() -> None:
        await history_manager.clear_history(1)
        assert history_manager._local_history[1] == deque()

    asyncio.run(run_test())