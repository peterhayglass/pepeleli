import os
import json

import boto3

from IConfigManager import IConfigManager
from ILogger import ILogger


class ConfigManager(IConfigManager):
    REGION = 'us-west-2' #this is stupid.  todo: fix


    def __init__(self, logger: ILogger) -> None:
        self.logger = logger
        self.ssm_client = boto3.client('ssm', region_name=self.REGION)
        self.PARAM_KEYS: list[str] = json.loads(
            self.ssm_client.get_parameter(Name="PARAM_KEYS", WithDecryption=True)['Parameter']['Value'])
        self.SECRETS_KEYS: list[str] = json.loads(
            self.ssm_client.get_parameter(Name="SECRETS_KEYS", WithDecryption=True)['Parameter']['Value'])
        self._load_parameters()
        self.logger.info("initialized configmanager")

        
    def _load_parameters(self) -> None:
        for param_name in (self.PARAM_KEYS + self.SECRETS_KEYS):
            value = self.ssm_client.get_parameter(Name=param_name, WithDecryption=True)['Parameter']['Value']
            os.environ[param_name] = value


    def get_parameter(self, key: str) -> str:
        return os.getenv(key, "")