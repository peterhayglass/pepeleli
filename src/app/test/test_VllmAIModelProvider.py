import pytest
from pytest import MonkeyPatch
from unittest.mock import AsyncMock, MagicMock
import asyncio
from typing import Any 
from collections import deque

from discord import Message

from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.vllm.VllmAIModelProvider import VllmAIModelProvider
from ai.vllm.VLLMClient import VLLMClient


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


def test_init_vllm(vllm_ai_model_provider: VllmAIModelProvider) -> None:
    assert vllm_ai_model_provider.RESPONSE_MODEL == "fake_vllm_response_model"
    assert vllm_ai_model_provider.MAX_CONTEXT_LEN == 4096


def test_get_response_vllm(
    vllm_ai_model_provider: VllmAIModelProvider, monkeypatch: MonkeyPatch
) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1
      
    monkeypatch.setattr(vllm_ai_model_provider.vllm, "generate_completion", AsyncMock(return_value={"text": ["Ai response"]}))
    monkeypatch.setattr(vllm_ai_model_provider.vllm, "get_token_usage", AsyncMock(return_value=50))

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        response = await vllm_ai_model_provider.get_response(msg)
        assert response == "Ai response"
    asyncio.run(run_test())


def test_add_user_message_vllm(vllm_ai_model_provider: VllmAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1
    
    monkeypatch.setattr(vllm_ai_model_provider.vllm, "generate_completion", AsyncMock(return_value={"text": ["Ai response"]}))
    monkeypatch.setattr(vllm_ai_model_provider.vllm, "get_token_usage", AsyncMock(return_value=50))

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        await vllm_ai_model_provider.add_user_message(msg)
        hist = await vllm_ai_model_provider.history_manager.get_history(msg.channel.id)
        assert hist[0].content == "User message"
    asyncio.run(run_test())     


def test_history_append_user_vllm(vllm_ai_model_provider: VllmAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    monkeypatch.setattr(vllm_ai_model_provider.vllm, "get_token_usage", AsyncMock(return_value=50))
    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        await vllm_ai_model_provider._history_append_user(msg)
        hist = await vllm_ai_model_provider.history_manager.get_history(msg.channel.id)
        assert hist[0].content == "User message"        
    asyncio.run(run_test())


def test_history_append_bot_vllm(vllm_ai_model_provider: VllmAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    channel_id = 1
    monkeypatch.setattr(vllm_ai_model_provider.vllm, "get_token_usage", AsyncMock(return_value=50))
    async def run_test() -> None:
        msg = MagicMock(spec=Message)
        msg.content = "Ai response"
        msg.channel.id = 1
        await vllm_ai_model_provider._init_async()
        await vllm_ai_model_provider._history_append_bot(msg)
        hist = await vllm_ai_model_provider.history_manager.get_history(msg.channel.id)
        assert hist[0].content == "Ai response"
    asyncio.run(run_test())


def test_check_history_len_vllm(vllm_ai_model_provider: VllmAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    monkeypatch.setattr(vllm_ai_model_provider.vllm, "get_token_usage", AsyncMock(return_value=500))

    async def run_test() -> None:
        await vllm_ai_model_provider._init_async()
        await vllm_ai_model_provider._history_append_bot(msg)
        hist = await vllm_ai_model_provider.history_manager.get_history(msg.channel.id)
        assert len(hist) == 1
    asyncio.run(run_test())