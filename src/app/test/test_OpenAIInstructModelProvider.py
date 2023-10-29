from collections import deque
import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock, AsyncMock
import asyncio
from typing import Any
from datetime import datetime
from decimal import Decimal

from discord import Message, User

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.openai.OpenAIInstructModelProvider import OpenAIInstructModelProvider
from HistoryManager import HistoryManager, HistoryItem


@pytest.fixture
def config_manager_instruct() -> IConfigManager:
    config_manager_instruct = MagicMock(spec=IConfigManager)
    fake_params = {
        "OPENAI_API_KEY": "fake_api_key",
        "OPENAI_INSTRUCT_PROVIDER_BASE_URI": "fake_base_uri",
        "OPENAI_INSTRUCT_RESPONSE_MODEL": "fake_instruct_response_model",
        "OPENAI_MAX_CONTEXT_LEN": "4096",
        "BOT_USERNAME": "BotUsername",
        "STOP_SEQUENCES": '["<messageID="]',
        "OPENAI_MODERATION_THRESHOLD": "0"
    }
    config_manager_instruct.get_parameter.side_effect = lambda param_name: fake_params[param_name]

    return config_manager_instruct


@pytest.fixture
def openai_instruct_model_provider(config_manager_instruct: IConfigManager, logger: ILogger) -> OpenAIInstructModelProvider:
    return OpenAIInstructModelProvider(config_manager_instruct, logger)


@pytest.fixture
def logger() -> ILogger:
    return MagicMock(spec=ILogger)


def test_init_instruct(openai_instruct_model_provider: OpenAIInstructModelProvider) -> None:
    assert openai_instruct_model_provider.RESPONSE_MODEL == "fake_instruct_response_model"
    assert openai_instruct_model_provider.MAX_CONTEXT_LEN == 4096


def test_get_response_instruct(
    openai_instruct_model_provider: OpenAIInstructModelProvider, monkeypatch: MonkeyPatch
) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    monkeypatch.setattr("ai.openai.OpenAIInstructModelProvider.HistoryManager._get_persisted_history", AsyncMock(return_value=deque()))

    monkeypatch.setattr(
        "openai.Completion.create",
        lambda model, prompt, max_tokens, stop: {
            "choices": [{"text": "Ai response"}]
        },
    )

    async def mock_get_moderation(text: str, channel_id: int) -> None:
        return None
    monkeypatch.setattr(openai_instruct_model_provider, "_get_moderation", mock_get_moderation)

    async def run_test() -> None:
        response = await openai_instruct_model_provider.get_response(msg)
        assert response == "Ai response"
    asyncio.run(run_test())


def test_add_user_message_instruct(
        openai_instruct_model_provider: OpenAIInstructModelProvider, 
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1
    msg.created_at = datetime.now()

    async def mock_get_moderation(text: str, channel_id: int) -> None:
        return None
    monkeypatch.setattr(openai_instruct_model_provider, "_get_moderation", mock_get_moderation)
    
    mock_history_append_user = AsyncMock()
    monkeypatch.setattr(openai_instruct_model_provider, "_history_append_user", mock_history_append_user)

    async def run_test() -> None:
        await openai_instruct_model_provider.add_user_message(msg)
        mock_history_append_user.assert_called_once_with(msg)

    asyncio.run(run_test())


def test_history_append_user(
        openai_instruct_model_provider: OpenAIInstructModelProvider, 
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author = MagicMock(spec=User)
    msg.author.display_name = "Username"
    msg.channel.id = 1
    msg.id = 1001
    msg.created_at = datetime.now()

    history_manager = MagicMock(spec=HistoryManager)
    add_history_item_mock = AsyncMock()
    history_manager.add_history_item = add_history_item_mock
    openai_instruct_model_provider.history_manager = history_manager

    async def verify_new_item() -> None:
        await openai_instruct_model_provider._history_append_user(msg)
        call_args = add_history_item_mock.call_args.args
        channel_id, new_item = call_args

        assert add_history_item_mock.call_count == 1
        assert channel_id == msg.channel.id
        assert new_item.content == msg.content
        assert new_item.name == msg.author.display_name
        assert new_item.id == msg.id
        assert new_item.channel_id == msg.channel.id
        assert new_item.timestamp == Decimal(msg.created_at.timestamp())

    asyncio.run(verify_new_item())


def test_history_append_bot(
        openai_instruct_model_provider: OpenAIInstructModelProvider, 
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "Bot message"
    msg.channel.id = 1
    msg.id = 2001
    msg.created_at = datetime.now()

    history_manager = MagicMock(spec=HistoryManager)
    add_history_item_mock = AsyncMock()
    history_manager.add_history_item = add_history_item_mock
    openai_instruct_model_provider.history_manager = history_manager

    async def verify_new_item() -> None:
        await openai_instruct_model_provider._history_append_bot(msg)
        call_args = add_history_item_mock.call_args.args
        channel_id, new_item = call_args

        assert add_history_item_mock.call_count == 1
        assert channel_id == msg.channel.id
        assert new_item.content == msg.content
        assert new_item.name == openai_instruct_model_provider.BOT_USERNAME
        assert new_item.id == msg.id
        assert new_item.channel_id == msg.channel.id
        assert new_item.timestamp == Decimal(msg.created_at.timestamp())

    asyncio.run(verify_new_item())