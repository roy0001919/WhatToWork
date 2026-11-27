from app.connectors.base import BaseJobConnector
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.lever import LeverConnector
from app.connectors.ashby import AshbyConnector
from app.connectors.remoteok import RemoteOKConnector
from app.connectors.himalayas import HimalayasConnector
from app.connectors.jobicy import JobicyConnector


CONNECTOR_REGISTRY: dict[str, type[BaseJobConnector]] = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "remoteok": RemoteOKConnector,
    "himalayas": HimalayasConnector,
    "jobicy": JobicyConnector,
}


def get_connector(source_type: str) -> type[BaseJobConnector]:
    connector = CONNECTOR_REGISTRY.get(source_type)

    if connector is None:
        raise ValueError(f"Unsupported source type: {source_type}")

    return connector
