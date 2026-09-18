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
    def read_records(self, table: str, cursor_field: str | None = None, cursor_value: str | None = None) -> Iterator[dict]:
        """Yield rows from the given table.

        Optional `cursor_field` and `cursor_value` can be provided to perform incremental reads.
        """
        ...


class DestinationConnector(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the connection works. Raise an exception if not."""
        ...

    @abstractmethod
    def discover(self) -> list[str]:
        """Return a list of destination tables/streams."""
        ...

    @abstractmethod
    def read_records(self, table: str, limit: int = 50, table_prefix: str = "") -> list[dict]:
        """Read rows from a destination table for previews or validation."""
        ...

    @abstractmethod
    def write_records(self, table: str, records: list[dict], table_prefix: str = "") -> None:
        """Write records to the destination, respecting write_mode."""
        ...

    def truncate_table(self, table: str) -> None:
        """Remove all rows from a destination table for a full refresh."""
        raise NotImplementedError("This destination connector does not support full refreshes")
        