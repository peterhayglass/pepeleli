import os
import boto3
from IConfigManager import IConfigManager
from ILogger import ILogger


class ConfigManager(IConfigManager):
    REGION = 'us-west-2' #this is stupid.  todo: fix
    PARAM_MAPPING = {
        'bot_token': 'BOT_TOKEN',
        'AI_PROVIDER_HOST': 'AI_PROVIDER_HOST'
    }


    def __init__(self, logger: ILogger) -> None:
        self.logger = logger
        self.ssm_client = boto3.client('ssm', region_name=self.REGION)
        self._load_parameters()
        self.logger.info("initialized configmanager")
        

    def _load_parameters(self) -> None:
        for param_name, env_var_name in self.PARAM_MAPPING.items():
            value = self.ssm_client.get_parameter(Name=param_name, WithDecryption=True)['Parameter']['Value']
            os.environ[env_var_name] = value


    def get_parameter(self, key: str) -> str:
        env_var_name = self.PARAM_MAPPING.get(key, "")
        return os.getenv(env_var_name, "")