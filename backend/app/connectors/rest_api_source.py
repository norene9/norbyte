import time

import requests
from typing import Iterator
from app.connectors.base import SourceConnector


class RestAPISourceConnector(SourceConnector):
    def _request_with_retry(self, url: str, headers: dict, auth, params: dict | None = None, max_retries: int = 5):
        last_error = None
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after is not None and retry_after.isdigit() else (2 ** attempt)
                if attempt == max_retries - 1:
                    raise ValueError(f"Rate limited after {max_retries} retries: {url}")
                time.sleep(wait_time)
                continue

            if resp.status_code >= 400:
                raise ValueError(f"API returned {resp.status_code} for {url}: {resp.text[:200]}")

            return resp

        if last_error is not None:
            raise last_error
        raise ValueError(f"Rate limited after {max_retries} retries: {url}")
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

        resp = self._request_with_retry(
            url,
            self._build_auth_headers(),
            self._build_auth(),
            params=None,
            max_retries=5,
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

        def _should_yield(record):
            if not cursor_field:
                return True
            record_cursor = record.get(cursor_field)
            if record_cursor is None:
                return False
            record_cursor_str = str(record_cursor)
            if cursor_value is None:
                return True
            return record_cursor_str > cursor_value

        if pagination_type == "none":
            resp = self._request_with_retry(url, headers, auth, params=None, max_retries=5)
            for record in self._extract_records(resp.json(), records_path):
                if _should_yield(record):
                    yield record

        elif pagination_type == "page_number":
            page = 1
            page_param = stream.get("page_param", "page")
            while True:
                resp = self._request_with_retry(url, headers, auth, params={page_param: page}, max_retries=5)
                records = self._extract_records(resp.json(), records_path)
                if not records:
                    break
                for record in records:
                    if _should_yield(record):
                        yield record
                page += 1
                time.sleep(0.2)

        elif pagination_type == "offset":
            offset = 0
            limit = stream.get("limit", 30)
            limit_param = stream.get("limit_param", "limit")
            offset_param = stream.get("offset_param", "offset")

            while True:
                params = {limit_param: limit, offset_param: offset}
                resp = self._request_with_retry(url, headers, auth, params=params, max_retries=5)
                records = self._extract_records(resp.json(), records_path)
                if not records:
                    break
                for record in records:
                    if _should_yield(record):
                        yield record
                if len(records) < limit:
                    break
                offset += limit
                time.sleep(0.2)

        elif pagination_type == "cursor":
            cursor_param = stream.get("cursor_param", "cursor")
            next_cursor_path = stream.get("next_cursor_path")
            if not next_cursor_path:
                raise ValueError(f"Stream '{table}' uses cursor pagination but is missing next_cursor_path")
            api_cursor = None
            while True:
                params = {cursor_param: api_cursor} if api_cursor else {}
                resp = self._request_with_retry(url, headers, auth, params=params, max_retries=5)
                body = resp.json()
                records = self._extract_records(body, records_path)
                for record in records:
                    if _should_yield(record):
                        yield record

                api_cursor = body
                for part in next_cursor_path.split("."):
                    api_cursor = api_cursor.get(part) if api_cursor else None
                if not api_cursor:
                    break
                time.sleep(0.2)

        else:
            raise ValueError(f"Unsupported pagination_type '{pagination_type}' for stream '{table}'")