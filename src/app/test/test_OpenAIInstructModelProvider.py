import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock, AsyncMock
import asyncio
from typing import Any
from discord import Message
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.OpenAIInstructModelProvider import OpenAIInstructModelProvider


@pytest.fixture
def config_manager_instruct() -> IConfigManager:
    config_manager_instruct = MagicMock(spec=IConfigManager)
    config_manager_instruct.get_parameter.side_effect = [
        "fake_api_key",
        "fake_instruct_response_model",
        "4096",
        "BotUsername",
        '["<messageID="]'
    ]
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

    monkeypatch.setattr(
        "openai.Completion.create",
        lambda model, prompt, max_tokens, stop: {
            "choices": [{"text": "Ai response"}]
        },
    )

    async def mock_get_moderation(text: str) -> None:
        return None
    monkeypatch.setattr(openai_instruct_model_provider, "_get_moderation", mock_get_moderation)

    async def run_test() -> None:
        response = await openai_instruct_model_provider.get_response(msg)
        assert response == "Ai response"
    asyncio.run(run_test())


def test_add_user_message_instruct(openai_instruct_model_provider: OpenAIInstructModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def mock_get_moderation(text: str) -> None:
        return None
    monkeypatch.setattr(openai_instruct_model_provider, "_get_moderation", mock_get_moderation)

    async def run_test() -> None:
        await openai_instruct_model_provider.add_user_message(msg)
        assert len(openai_instruct_model_provider.history[msg.channel.id]) == 1
        assert openai_instruct_model_provider.history[msg.channel.id][0]["content"] == "User message"
    asyncio.run(run_test())


def test_history_append_user_instruct(openai_instruct_model_provider: OpenAIInstructModelProvider) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def run_test() -> None:
        await openai_instruct_model_provider._history_append_user(msg)
        assert len(openai_instruct_model_provider.history[msg.channel.id]) == 1
        assert openai_instruct_model_provider.history[msg.channel.id][0]["content"] == "User message"
    asyncio.run(run_test())


def test_history_append_bot_instruct(openai_instruct_model_provider: OpenAIInstructModelProvider) -> None:
    channel_id = 1

    async def run_test() -> None:
        msg = MagicMock(spec=Message)
        msg.content = "Ai response"
        msg.channel.id = 1
        await openai_instruct_model_provider._history_append_bot(msg)
        assert len(openai_instruct_model_provider.history[channel_id]) == 1
        assert openai_instruct_model_provider.history[channel_id][0]["content"] == "Ai response"
    asyncio.run(run_test())


def test_check_history_len_instruct(openai_instruct_model_provider: OpenAIInstructModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    monkeypatch.setattr(openai_instruct_model_provider, "_count_tokens_list", AsyncMock(return_value=500))

    async def run_test() -> None:
        message = "Long message"
        await openai_instruct_model_provider._history_append_bot(msg)
        await openai_instruct_model_provider._check_history_len(msg.channel.id)
        assert len(openai_instruct_model_provider.history[msg.channel.id]) == 1
    
    asyncio.run(run_test())