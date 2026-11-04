from typing import Dict, Optional
from .base import BaseConnector
from .cloud_adapter import CloudAdapter
from .database_adapter import DatabaseAdapter
from .k8s_adapter import KubernetesAdapter
from .saas_adapter import SaaSAdapter
from .docker_connector import DockerConnector
from .process_connector import ProcessConnector

REGISTRY: Dict[str, BaseConnector] = {
    "docker-connector": DockerConnector(),
    "process-connector": ProcessConnector(),
    "cloud-adapter": CloudAdapter(),
    "database-adapter": DatabaseAdapter(),
    "k8s-adapter": KubernetesAdapter(),
    "saas-adapter": SaaSAdapter(),
}


def get_connector(connector_id: str) -> Optional[BaseConnector]:
    return REGISTRY.get(connector_id)
