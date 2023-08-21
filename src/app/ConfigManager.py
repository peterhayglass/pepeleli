import os
import boto3
from IConfigManager import IConfigManager


class ConfigManager(IConfigManager):
    REGION = 'us-west-2'
    PARAM_MAPPING = {
        'bot_token': 'BOT_TOKEN',
        'AI_MODEL_URI': 'AI_MODEL_URI',
    }

    def __init__(self) -> None:
        self.ssm_client = boto3.client('ssm', region_name=self.REGION)
        self._load_parameters()

    def _load_parameters(self) -> None:
        for param_name, env_var_name in self.PARAM_MAPPING.items():
            value = self.ssm_client.get_parameter(Name=param_name, WithDecryption=True)['Parameter']['Value']
            os.environ[env_var_name] = value

    def get_parameter(self, key: str) -> str:
        env_var_name = self.PARAM_MAPPING.get(key, "")
        return os.getenv(env_var_name, "")
