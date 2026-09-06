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

    def test_connection(self):
        base_url = self.config["base_url"].rstrip("/")
        resp = requests.get(f"{base_url}/health", headers=self._build_auth_headers(),
                            auth=self._build_auth(),
                            timeout=10
                            )
        if resp.status_code >= 400:
            raise Exception(f"Connection test failed with status code {resp.status_code}: {resp.text}")
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

        if pagination_type == "none":
            resp = requests.get(url, headers=headers, auth=auth, timeout=30)
            resp.raise_for_status()
            for record in self._extract_records(resp.json(), records_path):
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
                    yield record
                page += 1

        elif pagination_type == "cursor":
            cursor_param = stream.get("cursor_param", "cursor")
            next_cursor_path = stream["next_cursor_path"]
            cursor_value = None
            while True:
                params = {cursor_param: cursor_value} if cursor_value else {}
                resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
                resp.raise_for_status()
                body = resp.json()
                records = self._extract_records(body, records_path)
                for record in records:
                    yield record

                # walk the next_cursor_path to find the next page's cursor
                cursor_value = body
                for part in next_cursor_path.split("."):
                    cursor_value = cursor_value.get(part) if cursor_value else None
                if not cursor_value:
                    break