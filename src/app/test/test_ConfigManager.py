from typing import NamedTuple
import os
import pytest
from unittest.mock import patch, Mock
from ConfigManager import ConfigManager


class ConfigManagerTestSetup(NamedTuple):
    config_manager: ConfigManager
    mock_logger: Mock
    mock_ssm_client: Mock


@pytest.fixture(scope='function')
def setup() -> ConfigManagerTestSetup:
    mock_logger = Mock()
    mock_ssm_client = Mock()
    mock_ssm_client.get_parameter.return_value = {'Parameter': {'Value': 'some_value'}}
    
    with patch('boto3.client', return_value=mock_ssm_client):
        config_manager = ConfigManager(mock_logger)
    
    return ConfigManagerTestSetup(config_manager, mock_logger, mock_ssm_client)


def test_init(setup: ConfigManagerTestSetup) -> None:
    assert setup.config_manager.logger == setup.mock_logger


def test_load_parameters(setup: ConfigManagerTestSetup) -> None:
    param_values = {'bot_token': 'token123', 'AI_PROVIDER_HOST': 'http://example.com'}
    setup.mock_ssm_client.get_parameter.side_effect = (
        lambda Name, WithDecryption: 
            {'Parameter': {'Value': param_values[Name]}}
        )
    setup.config_manager._load_parameters()
    
    for param_name, env_var_name in setup.config_manager.PARAM_MAPPING.items():
        assert os.environ[env_var_name] == param_values[param_name]


def test_get_parameter_exists(setup: ConfigManagerTestSetup) -> None:
    os.environ['BOT_TOKEN'] = 'token123'
    assert setup.config_manager.get_parameter('bot_token') == 'token123'


def test_get_parameter_not_exists(setup: ConfigManagerTestSetup) -> None:
    assert setup.config_manager.get_parameter('nonexistent_key') == ''
