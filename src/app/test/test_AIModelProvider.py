from typing import NamedTuple, AsyncGenerator, Generator
import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from IConfigManager import IConfigManager
from ILogger import ILogger
from discord import Message
from AIModelProvider import AIModelProvider


class AIModelProviderTestSetup(NamedTuple):
    ai_model_provider: AIModelProvider
    mock_config_manager: Mock
    mock_logger: Mock
    mock_websocket: AsyncMock


async def mock_stream(message: Message, history: dict) -> AsyncGenerator[dict, None]:
    yield {'internal': [[1, 'Test response']]}


@pytest.fixture(scope='function')
def setup() -> Generator[AIModelProviderTestSetup, None, None]:
    mock_config_manager = Mock(spec=IConfigManager)
    mock_config_manager.get_parameter.return_value = 'http://example.com'
    mock_logger = Mock(spec=ILogger)
    mock_websocket = AsyncMock()
    ai_model_provider = AIModelProvider(mock_config_manager, mock_logger)
    
    yield AIModelProviderTestSetup(ai_model_provider, mock_config_manager, mock_logger, mock_websocket)


def test_init(setup: AIModelProviderTestSetup) -> None:
    assert setup.ai_model_provider.logger == setup.mock_logger
    assert setup.ai_model_provider.AI_PROVIDER_HOST == 'http://example.com'
    assert setup.ai_model_provider.URI == 'ws://http://example.com/api/v1/chat-stream'


@pytest.mark.asyncio
async def test_get_response(setup: AIModelProviderTestSetup) -> None:
    mock_message = Mock(spec=Message)
    mock_message.content = "Test message"
    with patch.object(setup.ai_model_provider, '_stream_response', new=mock_stream):
        response = await setup.ai_model_provider.get_response(mock_message)

    assert response == 'Test response'


@pytest.mark.asyncio
async def test_stream_response(setup: AIModelProviderTestSetup) -> None:
    mock_message = Mock(spec=Message)
    mock_message.content = "Test message"

    with patch.object(setup.ai_model_provider, '_stream_response', new=mock_stream):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_websockets_connect:
            mock_websockets_connect.return_value.__aenter__.return_value = setup.mock_websocket
            setup.mock_websocket.recv.return_value = '{"event": "text_stream", "history": {"internal": [[1, "Test response"]]}}'
            mock_history = setup.ai_model_provider.BLANK_HISTORY

            # Convert the generator to a list to examine the output
            response_gen = setup.ai_model_provider._stream_response(mock_message, mock_history)
            response_list = [r async for r in response_gen]

    assert response_list == [{'internal': [[1, 'Test response']]}]


def test_construct_payload(setup: AIModelProviderTestSetup) -> None:
    mock_message = Mock(spec=Message)
    mock_message.content = "Test message"
    mock_message.author.display_name = "Test Author"
    mock_history = {'internal': [[1, 'Test response']]}
    
    payload = setup.ai_model_provider._construct_payload(mock_message, mock_history)
    
    assert payload['user_input'] == "Test message"
    assert payload['your_name'] == "Test Author"