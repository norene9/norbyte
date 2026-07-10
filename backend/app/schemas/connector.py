from pydantic import BaseModel

class ConnectionPayload(BaseModel):
    source_name: str
    api_key: str
    sync_frequency_minutes: int
