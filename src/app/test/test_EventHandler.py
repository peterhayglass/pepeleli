import pytest
from unittest.mock import AsyncMock, Mock
from discord import Message
from ILogger import ILogger
from EventHandler import EventHandler


@pytest.fixture
def mock_enqueue_message() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_logger() -> Mock:
    return Mock(spec=ILogger)


@pytest.fixture
def mock_message() -> Mock:
    msg = Mock(spec=Message)
    msg.author.bot = False
    msg.guild = Mock()
    msg.guild.me = Mock()
    msg.mentions = [msg.guild.me]
    msg.content = "test message"
    return msg


@pytest.fixture
def event_handler(mock_enqueue_message: AsyncMock, mock_logger: Mock) -> EventHandler:
    return EventHandler(mock_enqueue_message, mock_logger)


@pytest.mark.asyncio
async def test_on_message_bot_author(
    event_handler: EventHandler, 
    mock_message: Mock, 
    mock_logger: Mock,
    mock_enqueue_message: AsyncMock
) -> None:
        mock_message.author.bot = True
        await event_handler.on_message(mock_message)
        mock_logger.info.assert_called()
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
        mock_logger.info.assert_called()
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