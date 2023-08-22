from typing import Any
from abc import ABC, abstractmethod


class ILogger(ABC):
    @abstractmethod
    def info(self, message: str, *args: Any) -> None:
        """Logs an informational message."""
        pass
    

    @abstractmethod
    def debug(self, message: str, *args: Any) -> None:
        """Logs a debug message."""
        pass


    @abstractmethod
    def warning(self, message: str, *args: Any) -> None:
        """Logs a warning message."""
        pass


    @abstractmethod
    def error(self, message: str, *args: Any) -> None:
        """Logs an error message."""
        pass


    @abstractmethod
    def exception(self, message: str, exception: Exception, *args: Any) -> None:
        """Logs an exception with details."""
        pass
