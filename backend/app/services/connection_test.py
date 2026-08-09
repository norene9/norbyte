from fastapi import HTTPException

from app.connectors.registry import get_destination_connector, get_source_connector


def test_source_connection(connector_type: str, config: dict) -> None:
    connector_cls = get_source_connector(connector_type)
    connector = connector_cls(config)
    try:
        connector.test_connection()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Source connection failed: {exc}") from exc


def test_destination_connection(connector_type: str, config: dict) -> None:
    connector_cls = get_destination_connector(connector_type)
    connector = connector_cls(config)
    try:
        connector.test_connection()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Destination connection failed: {exc}") from exc
