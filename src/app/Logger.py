from winreg import REG_BINARY
import boto3
import datetime
from ILogger import ILogger
from typing import Any


class Logger(ILogger):
    REGION = 'us-west-2' #this is stupid.  todo: fix
    def __init__(self, log_group_name: str = "ecs-logs"):
        self.client = boto3.client('logs', region_name=self.REGION)
        self.log_group_name = log_group_name
        self.log_stream_name = self.create_log_stream()


    def create_log_stream(self) -> str:
        log_stream_name = f"pepeleli-log-stream-{int(datetime.datetime.now().timestamp())}"
        self.client.create_log_stream(
            logGroupName=self.log_group_name,
            logStreamName=log_stream_name,
        )
        return log_stream_name


    def put_log(self, message: str) -> None:
        timestamp = int(datetime.datetime.now().timestamp() * 1000) # CloudWatch expects milliseconds
        self.client.put_log_events(
            logGroupName=self.log_group_name,
            logStreamName=self.log_stream_name,
            logEvents=[
                {
                    'timestamp': timestamp,
                    'message': message
                }
            ]
        )


    def info(self, message: str, *args: Any) -> None:
        self.put_log(f"INFO: {message.format(*args)}")


    def debug(self, message: str, *args: Any) -> None:
        self.put_log(f"DEBUG: {message.format(*args)}")


    def warning(self, message: str, *args: Any) -> None:
        self.put_log(f"WARNING: {message.format(*args)}")


    def error(self, message: str, *args: Any) -> None:
        self.put_log(f"ERROR: {message.format(*args)}")


    def exception(self, message: str, exception: Exception, *args: Any) -> None:
        self.put_log(f"EXCEPTION: {message.format(*args)}\nDetails: {str(exception)}")
