import pytest
from pytest import MonkeyPatch
from unittest.mock import MagicMock, AsyncMock
import asyncio
from typing import Any
from discord import Message
from IConfigManager import IConfigManager
from ILogger import ILogger
from ai.openai.OpenAIModelProvider import OpenAIModelProvider


@pytest.fixture
def config_manager() -> IConfigManager:
    config_manager = MagicMock(spec=IConfigManager)
    config_manager.get_parameter.side_effect = [
        "fake_api_key",
        "fake_response_model",
        "4096",
    ]
    return config_manager


@pytest.fixture
def logger() -> ILogger:
    return MagicMock(spec=ILogger)


@pytest.fixture
def openai_model_provider(config_manager: IConfigManager, logger: ILogger) -> OpenAIModelProvider:
    return OpenAIModelProvider(config_manager, logger)


def test_init(openai_model_provider: OpenAIModelProvider) -> None:
    assert openai_model_provider.RESPONSE_MODEL == "fake_response_model"
    assert openai_model_provider.MAX_CONTEXT_LEN == 4096


def test_get_response(openai_model_provider: OpenAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def mock_chat_completion(*args: Any, **kwargs: Any) -> dict:
        completion = {"choices": [{"message": {"content": "Ai response"}}]}
        return completion

    monkeypatch.setattr("openai.ChatCompletion.acreate", mock_chat_completion)

    async def run_test() -> None:
        response = await openai_model_provider.get_response(msg)
        assert response == "Ai response"
    asyncio.run(run_test())


def test_add_user_message(openai_model_provider: OpenAIModelProvider) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def run_test() -> None:
        await openai_model_provider.add_user_message(msg)
        assert len(openai_model_provider.history[msg.channel.id]) == 1
        assert openai_model_provider.history[msg.channel.id][0]["content"] == "User message"
    asyncio.run(run_test())


def test_history_append_user(openai_model_provider: OpenAIModelProvider) -> None:
    msg = MagicMock(spec=Message)
    msg.content = "User message"
    msg.author.display_name = "Username"
    msg.channel.id = 1

    async def run_test() -> None:
        await openai_model_provider._history_append_user(msg)
        assert len(openai_model_provider.history[msg.channel.id]) == 1
        assert openai_model_provider.history[msg.channel.id][0]["content"] == "User message"
    asyncio.run(run_test())


def test_history_append_bot(openai_model_provider: OpenAIModelProvider) -> None:
    channel_id = 1

    async def run_test() -> None:
        message = "Ai response"
        await openai_model_provider._history_append_bot(message, channel_id)
        assert len(openai_model_provider.history[channel_id]) == 1
        assert openai_model_provider.history[channel_id][0]["content"] == "Ai response"
    asyncio.run(run_test())


def test_check_history_len(openai_model_provider: OpenAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    channel_id = 1

    def mock_count_tokens(*args: Any, **kwargs: Any) -> int:
        return 500

    monkeypatch.setattr(openai_model_provider, "_count_tokens", mock_count_tokens)

    async def run_test() -> None:
        message = "Long message"
        await openai_model_provider._history_append_bot(message, channel_id)
        await openai_model_provider._check_history_len(channel_id)
        assert len(openai_model_provider.history[channel_id]) == 1
    
    asyncio.run(run_test())


def test_count_tokens(openai_model_provider: OpenAIModelProvider, monkeypatch: MonkeyPatch) -> None:
    def mock_get_encoding(*args: Any, **kwargs: Any) -> list[int]:
        encoding = MagicMock()
        encoding.encode.return_value = [1, 2, 3, 4, 5]
        return encoding

    monkeypatch.setattr("tiktoken.get_encoding", mock_get_encoding)

    token_count = openai_model_provider._count_tokens([{"content": "test string", "name": "test_name"}])
    assert token_count == (5 + 5 + 3 + 1 + 3)
    #5 each for the two mock encodings (the message and the name), 
    #plus 3 per message for the one message
    #plus 1 per name for the one name
    #plus 3 to prime the model to respond
    #this is valid for gpt-3.5-turbo-0613 and all versions to date of gpt-4
    #see section 6 at https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb