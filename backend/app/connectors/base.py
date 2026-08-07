from abc import ABC, abstractmethod
from typing import Any, Iterator


class SourceConnector(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the connection works. Raise an exception if not."""
        ...

    @abstractmethod
    def discover(self) -> list[str]:
        """Return a list of available tables/streams."""
        ...

    @abstractmethod
    def read_records(self, table: str) -> Iterator[dict]:
        """Yield rows from the given table."""
        ...


class DestinationConnector(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the connection works. Raise an exception if not."""
        ...

    @abstractmethod
    def write_records(self, table: str, records: list[dict]) -> None:
        """Write records to the destination, respecting write_mode."""
        ...
        