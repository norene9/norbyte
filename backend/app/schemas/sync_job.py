from typing import Optional

from pydantic import BaseModel


class SyncJobResponse(BaseModel):
    id: int
    connection_id: int
    status: str
    started_at: Optional[str] = None
    records_processed: Optional[int] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None
    logs: Optional[str] = None

    class Config:
        from_attributes = True
