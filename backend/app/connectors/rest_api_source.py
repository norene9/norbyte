import requests
from typing import Iterator
from app.connectors.base import SourceConnector


class RestAPISourceConnector(SourceConnector):
    def _build_auth_headers(self) -> dict:
        auth_type = self.config.get("auth_type", "none")
        headers = {}
        if auth_type in ("api_key_header", "api_key_hader"):
            header_name = self.config.get("api_key_header_name", "X-API-Key")
            headers[header_name] = self.config.get("api_key")
        elif auth_type == "bearer_token":
            headers["Authorization"] = f"Bearer {self.config.get('bearer_token')}"
        return headers

    def _build_auth(self):
        if self.config.get("auth_type") == "basic_auth":
            return (self.config.get("username"), self.config.get("password"))
        return None

    def test_connection(self) -> bool:
        streams = self.config.get("streams", [])
        if not streams:
            raise ValueError("No streams configured to test against")

        base_url = self.config["base_url"].rstrip("/")
        first_stream = streams[0]
        url = f'{base_url}{first_stream["path"]}'

        resp = requests.get(
            url,
            headers=self._build_auth_headers(),
            auth=self._build_auth(),
            timeout=10,
        )
        if resp.status_code >= 400:
            raise ValueError(f"API returned {resp.status_code} for {url}: {resp.text[:200]}")
        return True
    def discover(self) -> list[str]:
        return [s["name"] for s in self.config.get("streams", [])]
    def _get_stream_config(self, stream_name: str) -> dict:
        for s in self.config.get("streams", []):
            if s["name"] == stream_name:
                return s
        raise ValueError(f"Stream '{stream_name}' not found in config")

    def _extract_records(self, response_json, records_path: str) -> list[dict]:
        if not records_path:
            return response_json  # top-level array
        data = response_json
        for part in records_path.split("."):
            data = data[part]
        return data

    def read_records(
        self,
        table: str,
        cursor_field: str | None = None,
        cursor_value: str | None = None,
    ) -> Iterator[dict]:
        stream = self._get_stream_config(table)
        base_url = self.config["base_url"].rstrip("/")
        url = f'{base_url}{stream["path"]}'
        records_path = stream.get("records_path", "")
        pagination_type = stream.get("pagination_type", "none")

        headers = self._build_auth_headers()
        auth = self._build_auth()

        # Incremental filtering: if cursor_field is provided, only yield records where cursor_field > cursor_value
        def _should_yield(record):
            if not cursor_field:
                return True
            record_cursor = record.get(cursor_field)
            if record_cursor is None:
                return False
            # Convert both to strings for comparison (cursor_value is already a string from SyncState)
            record_cursor_str = str(record_cursor)
            if cursor_value is None:
                return True
            return record_cursor_str > cursor_value

        if pagination_type == "none":
            resp = requests.get(url, headers=headers, auth=auth, timeout=30)
            resp.raise_for_status()
            for record in self._extract_records(resp.json(), records_path):
                if _should_yield(record):
                    yield record

        elif pagination_type == "page_number":
            page = 1
            page_param = stream.get("page_param", "page")
            while True:
                resp = requests.get(url, headers=headers, auth=auth, params={page_param: page}, timeout=30)
                resp.raise_for_status()
                records = self._extract_records(resp.json(), records_path)
                if not records:
                    break
                for record in records:
                    if _should_yield(record):
                        yield record
                page += 1

        elif pagination_type == "cursor":
            cursor_param = stream.get("cursor_param", "cursor")
            next_cursor_path = stream["next_cursor_path"]
            api_cursor = None
            while True:
                params = {cursor_param: api_cursor} if api_cursor else {}
                resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
                resp.raise_for_status()
                body = resp.json()
                records = self._extract_records(body, records_path)
                for record in records:
                    if _should_yield(record):
                        yield record

                # walk the next_cursor_path to find the next page's cursor
                api_cursor = body
                for part in next_cursor_path.split("."):
                    api_cursor = api_cursor.get(part) if api_cursor else None
                if not api_cursor:
                    break