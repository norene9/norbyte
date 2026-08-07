from app.connectors.postgres_source import PostgresSourceConnector
from app.connectors.postgres_destination import PostgresDestinationConnector

SOURCE_CONNECTOR_REGISTRY = {
    "postgres": PostgresSourceConnector,
}

DESTINATION_CONNECTOR_REGISTRY = {
    "postgres": PostgresDestinationConnector,
}


def get_source_connector(connector_type: str):
    connector_cls = SOURCE_CONNECTOR_REGISTRY.get(connector_type)
    if not connector_cls:
        raise ValueError(f"No source connector registered for type '{connector_type}'")
    return connector_cls


def get_destination_connector(connector_type: str):
    connector_cls = DESTINATION_CONNECTOR_REGISTRY.get(connector_type)
    if not connector_cls:
        raise ValueError(f"No destination connector registered for type '{connector_type}'")
    return connector_cls