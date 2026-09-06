from app.connectors.postgres_source import PostgresSourceConnector
from app.connectors.postgres_destination import PostgresDestinationConnector
from app.connectors.rest_api_source import RestAPISourceConnector

SOURCE_CONNECTOR_REGISTRY = {
    "postgres": PostgresSourceConnector,
    "rest_api": RestAPISourceConnector,
}

DESTINATION_CONNECTOR_REGISTRY = {
    "postgres": PostgresDestinationConnector,
}


def list_connector_types(source_or_destination: str) -> list[str]:
    registries = {
        "source": SOURCE_CONNECTOR_REGISTRY,
        "destination": DESTINATION_CONNECTOR_REGISTRY,
    }
    try:
        return list(registries[source_or_destination.lower()])
    except KeyError as exc:
        raise ValueError("source_or_destination must be 'source' or 'destination'") from exc


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