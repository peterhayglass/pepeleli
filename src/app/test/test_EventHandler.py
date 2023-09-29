import pytest
import time
from time import sleep
from unittest.mock import AsyncMock, Mock
from discord import Message
from ILogger import ILogger
from EventHandler import EventHandler
from IConfigManager import IConfigManager


@pytest.fixture
def mock_enqueue_message() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_remember_message() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_logger() -> Mock:
    return Mock(spec=ILogger)


@pytest.fixture
def mock_config_manager() -> Mock:
    config_manager = Mock(spec=IConfigManager)
    
    def mock_get_parameter(key: str) -> str:
        if key == "MONITOR_CHANNELS":
            return '["mock_channel_id_1", "mock_channel_id_2"]'
        elif key == "RATE_LIMITS":
            return '{ "tier_1": {"messages": 8, "interval": 60}, "tier_2": {"messages": 15, "interval": 300} }'
        else:
            return f"mock_value_for_{key}"
            
    config_manager.get_parameter.side_effect = mock_get_parameter
    return config_manager


@pytest.fixture
def mock_message() -> Mock:
    msg = Mock(spec=Message)
    msg.author.bot = False
    msg.guild = Mock()
    msg.guild.me = Mock()
    msg.mentions = [msg.guild.me]
    msg.content = "test message"
    msg.channel.id = "mock_channel_id_1"
    msg.channel.send = AsyncMock()
    return msg


@pytest.fixture
def event_handler(
    mock_enqueue_message: AsyncMock, 
    mock_remember_message: AsyncMock, 
    mock_config_manager: Mock,
    mock_logger: Mock
) -> EventHandler:
        return EventHandler(mock_enqueue_message, mock_remember_message, mock_config_manager, mock_logger)



@pytest.mark.asyncio
async def test_on_message_bot_author(
    event_handler: EventHandler, 
    mock_message: Mock, 
    mock_logger: Mock,
    mock_enqueue_message: AsyncMock,
    mock_config_manager: Mock
) -> None:
        mock_message.author.bot = True
        await event_handler.on_message(mock_message)
        mock_enqueue_message.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_normal(
    event_handler: EventHandler, 
    mock_message: Mock, 
    mock_enqueue_message: AsyncMock, 
    mock_logger: Mock
) -> None:
        await event_handler.on_message(mock_message)
        mock_enqueue_message.assert_called_with(mock_message)


@pytest.mark.asyncio
async def test_on_message_mention(
    event_handler: EventHandler, 
    mock_message: Mock, 
    mock_enqueue_message: AsyncMock, 
    mock_logger: Mock
) -> None:
        mock_message.guild = Mock()
        mock_message.guild.me = Mock()
        mock_message.mentions = [mock_message.guild.me]
        
        await event_handler.on_message(mock_message)
        mock_enqueue_message.assert_called_with(mock_message)


@pytest.mark.asyncio
async def test_on_message_with_guild_bot_not_mentioned(
    event_handler: EventHandler,
    mock_message: Mock,
    mock_enqueue_message: AsyncMock
) -> None:
        mock_message.guild = Mock()
        mock_message.mentions = []
        
        await event_handler.on_message(mock_message)
        mock_enqueue_message.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_enqueue_message_exception(
    event_handler: EventHandler,
    mock_message: Mock,
    mock_enqueue_message: AsyncMock,
    mock_logger: Mock
) -> None:
        mock_enqueue_message.side_effect = Exception("Some error")
        await event_handler.on_message(mock_message)
        mock_logger.exception.assert_called()


@pytest.mark.asyncio
async def test_on_message_rate_limit(
    event_handler: EventHandler,
    mock_message: Mock,
    mock_enqueue_message: AsyncMock,
    mock_logger: Mock,
    mock_config_manager: Mock
) -> None:
        for i in range(10):
            await event_handler.on_message(mock_message)
        assert mock_enqueue_message.call_count == 8
        assert mock_logger.info.call_count == 2  #2 messages should have been rate limited


@pytest.mark.asyncio
async def test_on_message_replace_mentions(
    event_handler: EventHandler,
    mock_message: Mock,
) -> None:
        mock_message.content = "<@12345> <@!67890>"
        mock_message.guild.get_member.side_effect = lambda user_id: Mock(display_name=f"User{user_id}")
        
        replaced_content = await event_handler._replace_mentions(mock_message)
        assert replaced_content == "@User12345 @User67890"


async def set_mock_message_history(
    mock_event_handler: EventHandler, 
    user_id: int, 
    delay: int, 
    count: int) -> None:
    """
    Add dummy timestamps to the user's message history for testing purposes.
    
    Args:
        mock_event_handler (EventHandler): The mocked EventHandler object with user_message_history
        user_id (int): The user ID whose message history is being manipulated
        delay (int): The delay between consecutive messages in seconds
        count (int): The number of dummy timestamps to be added

    Returns: None
    """
    now = time.time()
    timestamps = [(now - i * delay) for i in range(count)]
    mock_event_handler.user_message_history[user_id] = timestamps