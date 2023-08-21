import os
import boto3
from IConfigManager import IConfigManager

class ConfigManager(IConfigManager):
    """Implementation of the Configuration Manager"""

    REGION = 'us-west-2'

    def __init__(self) -> None:
        self.ssm_client = boto3.client('ssm', region_name=self.REGION)
        self._load_bot_token()

    def _load_bot_token(self) -> None:
        """Retrieve bot token from SSM and store it as an env var"""
        bot_token = self.ssm_client.get_parameter(Name='bot_token', WithDecryption=True)
        os.environ['BOT_TOKEN'] = bot_token['Parameter']['Value']

    def get_bot_token(self) -> str:
        """Retrieve bot token from env var"""
        return os.getenv('BOT_TOKEN', "")
