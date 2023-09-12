import pytest
from unittest.mock import patch, Mock, ANY
from typing import NamedTuple
from Logger import Logger


class LoggerTestSetup(NamedTuple):
    logger: Logger
    mock_log_client: Mock


@pytest.fixture(scope='function')
def setup() -> LoggerTestSetup:
    with patch('boto3.client') as mock_client:
        mock_log_client = Mock()
        mock_client.return_value = mock_log_client
        logger = Logger("test-log-group")
        mock_log_client.create_log_stream.assert_called_once()
        return LoggerTestSetup(logger, mock_log_client)


def test_init(setup: LoggerTestSetup) -> None:
    assert setup.logger.log_group_name == "test-log-group"


def test_put_log(setup: LoggerTestSetup) -> None:
    message = 'Test Message'
    setup.logger.put_log(message)
    setup.mock_log_client.put_log_events.assert_called_once()


def test_info(setup: LoggerTestSetup) -> None:
    message = 'Info Message {}'
    setup.logger.info(message, 'test')
    setup.mock_log_client.put_log_events.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = setup.logger.log_stream_name,
        logEvents=[{'timestamp': ANY, 'message': 'INFO: Info Message test'}]
    )


def test_debug(setup: LoggerTestSetup) -> None:
    message = 'Debug Message {}'
    setup.logger.debug(message, 'test')
    setup.mock_log_client.put_log_events.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = setup.logger.log_stream_name,
        logEvents = [{'timestamp': ANY, 'message': 'DEBUG: Debug Message test'}]
    )


def test_warning(setup: LoggerTestSetup) -> None:
    message = 'Warning Message {}'
    setup.logger.warning(message, 'test')
    setup.mock_log_client.put_log_events.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = setup.logger.log_stream_name,
        logEvents = [{'timestamp': ANY, 'message': 'WARNING: Warning Message test'}]
    )


def test_error(setup: LoggerTestSetup) -> None:
    message = 'Error Message {}'
    setup.logger.error(message, 'test')
    setup.mock_log_client.put_log_events.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = setup.logger.log_stream_name,
        logEvents = [{'timestamp': ANY, 'message': 'ERROR: Error Message test'}]
    )


def test_exception(setup: LoggerTestSetup) -> None:
    message = 'Exception Message {}'
    exception = ValueError("test exception")
    with patch('traceback.format_exc') as mock_traceback:
        mock_traceback.return_value = 'Traceback details'
        setup.logger.exception(message, exception, 'test')
    
    expected_message = 'EXCEPTION: Exception Message test\nDetails: test exception\nTraceback:\nTraceback details'
    setup.mock_log_client.put_log_events.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = setup.logger.log_stream_name,
        logEvents = [{'timestamp': ANY, 'message': expected_message}]
    )


def test_create_log_stream(setup: LoggerTestSetup) -> None:
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value.timestamp.return_value = 1234567890
        stream_name = setup.logger.create_log_stream()

    expected_stream_name = 'pepeleli-log-stream-1234567890'
    assert stream_name == expected_stream_name
    setup.mock_log_client.create_log_stream.assert_called_with(
        logGroupName = setup.logger.log_group_name,
        logStreamName = expected_stream_name
    )