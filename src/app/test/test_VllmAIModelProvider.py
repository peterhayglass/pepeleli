import pytest
from pytest import MonkeyPatch
from unittest.mock import AsyncMock, MagicMock
import asyncio
from typing import Any 
from collections import deque
from datetime import datetime
from decimal import Decimal

from discord import Message, User

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.vllm.VllmAIModelProvider import VllmAIModelProvider
from ai.vllm.VLLMClient import VLLMClient
from HistoryManager import HistoryManager


@pytest.fixture
def config_manager_vllm() -> IConfigManager:
    config_manager_vllm = MagicMock(spec=IConfigManager)
    fake_params = {
        "BOT_USERNAME": "BotUsername",
        "VLLM_MAX_CONTEXT_LEN": "4096",
        "VLLM_RESPONSE_MODEL": "fake_vllm_response_model",
        "VLLM_AI_PROVIDER_HOST": "localhost",
        "VLLM_AI_PROVIDER_PORT": "8888",
        "VLLM_API_KEY": "fake_vllm_api_key",
        "STOP_SEQUENCES": '["<messageID="]'
    }
    config_manager_vllm.get_parameter.side_effect = lambda param_name: fake_params[param_name]

    return config_manager_vllm


@pytest.fixture
def vllm_ai_model_provider(config_manager_vllm: IConfigManager, logger: ILogger) -> VllmAIModelProvider:
    vllm = VllmAIModelProvider(config_manager_vllm, logger)
    return vllm


@pytest.fixture
def logger() -> ILogger:
    return MagicMock(spec=ILogger)

@pytest.fixture
def mock_vllmclient(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("ai.vllm.VllmAIModelProvider.VLLMClient.generate_completion", AsyncMock(return_value={"text": ["Ai response"]}))
    monkeypatch.setattr("ai.vllm.VllmAIModelProvider.VLLMClient.get_token_usage", AsyncMock(return_value=50))


def test_init_vllm(vllm_ai_model_provider: VllmAIModelProvider) -> None:
    assert vllm_ai_model_provider.RESPONSE_MODEL == "fake_vllm_response_model"
    assert vllm_ai_model_provider.MAX_CONTEXT_LEN == 4096


def test_get_response_vllm(
    vllm_ai_model_provider: VllmAIModelProvider, 
    mock_vllmclient: None,
    monkeypatch: MonkeyPatch
) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        response = await vllm_ai_model_provider.get_response(msg)
        assert response == "Ai response"
    asyncio.run(run_test())


def test_add_user_message_vllm(
        vllm_ai_model_provider: VllmAIModelProvider,
        mock_vllmclient: None, 
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1
    msg.created_at = datetime.now()
    
    mock_history_append_user = AsyncMock()
    monkeypatch.setattr(vllm_ai_model_provider, "_history_append_user", mock_history_append_user)

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        await vllm_ai_model_provider.add_user_message(msg)
        mock_history_append_user.assert_called_once_with(msg)

    asyncio.run(run_test())     


def test_history_append_user_vllm(
        vllm_ai_model_provider: VllmAIModelProvider,
        mock_vllmclient: None, 
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author = MagicMock(spec=User)
    msg.author.display_name = "Username"
    msg.channel.id = 1
    msg.id = 1001
    msg.created_at = datetime.now()

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        
        history_manager = MagicMock(spec=HistoryManager)
        add_history_item_mock = AsyncMock()
        history_manager.add_history_item = add_history_item_mock
        vllm_ai_model_provider.history_manager = history_manager
        
        await vllm_ai_model_provider._history_append_user(msg)
        call_args = add_history_item_mock.call_args.args
        channel_id, new_item = call_args

        assert add_history_item_mock.call_count == 1
        assert channel_id == msg.channel.id
        assert new_item.content == msg.content
        assert new_item.name == msg.author.display_name
        assert new_item.id == msg.id
        assert new_item.channel_id == msg.channel.id
        assert new_item.timestamp == Decimal(msg.created_at.timestamp())
     
    asyncio.run(run_test())


def test_history_append_bot_vllm(
        vllm_ai_model_provider: VllmAIModelProvider, 
        mock_vllmclient: None,
        monkeypatch: MonkeyPatch
        ) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "Bot message"
    msg.channel.id = 1
    msg.id = 2001
    msg.created_at = datetime.now()

    async def verify_new_item() -> None:
        await vllm_ai_model_provider._init_async()

        history_manager = MagicMock(spec=HistoryManager)
        add_history_item_mock = AsyncMock()
        history_manager.add_history_item = add_history_item_mock
        vllm_ai_model_provider.history_manager = history_manager
        
        await vllm_ai_model_provider._history_append_bot(msg)
        call_args = add_history_item_mock.call_args.args
        channel_id, new_item = call_args

        assert add_history_item_mock.call_count == 1
        assert channel_id == msg.channel.id
        assert new_item.content == msg.content
        assert new_item.name == vllm_ai_model_provider.BOT_USERNAME
        assert new_item.id == msg.id
        assert new_item.channel_id == msg.channel.id
        assert new_item.timestamp == Decimal(msg.created_at.timestamp())

    asyncio.run(verify_new_item())

