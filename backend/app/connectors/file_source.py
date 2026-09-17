# app/connectors/file_source.py
import pandas as pd
from typing import Iterator
from app.connectors.base import SourceConnector


class FileSourceConnector(SourceConnector):
    def _iter_file_entries(self) -> list[dict]:
        """Normalize config into a list of file entries, supporting both the legacy
        single-file config and the newer multi-file ("files") config."""
        if "files" in self.config:
            return self.config["files"]
        entry = dict(self.config)
        entry.setdefault("stream_name", "data")
        return [entry]

    def _get_file_entry(self, table: str) -> dict:
        for entry in self._iter_file_entries():
            if entry.get("stream_name", "data") == table:
                return entry
        raise ValueError(f"No uploaded file found for stream '{table}'")

    def _load_dataframe(self, table: str) -> pd.DataFrame:
        entry = self._get_file_entry(table)
        file_path = entry["file_path"]
        file_type = entry["file_type"]
        header = 0 if entry.get("has_header", True) else None

        if file_type == "csv":
            return pd.read_csv(file_path, header=header)
        elif file_type == "xlsx":
            sheet = entry.get("sheet_name", 0)
            return pd.read_excel(file_path, sheet_name=sheet, header=header)
        else:
            raise ValueError(f"Unsupported file_type: {file_type}")

    def test_connection(self) -> bool:
        return all(len(self._load_dataframe(entry.get("stream_name", "data")).columns) > 0 for entry in self._iter_file_entries())

    def discover(self) -> list[str]:
        # each uploaded file is its own stream, named after the file itself
        return [entry.get("stream_name", "data") for entry in self._iter_file_entries()]

    def read_records(self, table: str, cursor_field: str | None = None, cursor_value: str | None = None) -> Iterator[dict]:
        df = self._load_dataframe(table)
        df = df.where(pd.notnull(df), None)  # convert NaN → None for clean JSON/SQL handling
        for record in df.to_dict(orient="records"):
            yield record

    def get_table_schema(self, table: str) -> list[dict]:
        df = self._load_dataframe(table)
        # int64 must map to bigint, not integer, since pandas int64 values can exceed Postgres's 4-byte integer range
        type_map = {"int64": "bigint", "float64": "double precision", "bool": "boolean", "object": "text", "datetime64[ns]": "timestamp"}
        return [
            {"name": col, "data_type": type_map.get(str(dtype), "text"), "max_length": None, "nullable": True}
            for col, dtype in df.dtypes.items()
        ]