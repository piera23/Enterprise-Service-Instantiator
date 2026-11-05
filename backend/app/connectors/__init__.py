# ==============================================================================
# CONNECTORS/__INIT__.PY - Registry Centrale dei Connettori di Esecuzione
# Centralizza e mappa tutti i driver di provisioning supportati dalla piattaforma
# ==============================================================================

# Tipizzazione Python per dizionari e valori opzionali
from typing import Dict, Optional
# Classe base astratta per tutti i connettori
from .base import BaseConnector
# Connettore per ambienti Cloud (AWS, Azure, GCP via Terraform/OpenTofu)
from .cloud_adapter import CloudAdapter
# Connettore per Database as a Service (PostgreSQL, MySQL, Redis) con HashiCorp Vault
from .database_adapter import DatabaseAdapter
# Connettore per cluster Kubernetes, repository Git e pipeline CI/CD
from .k8s_adapter import KubernetesAdapter
# Connettore per workspace SaaS esterni e integrazioni API partner
from .saas_adapter import SaaSAdapter
# Connettore reale per Docker Engine (container reali e porte dinamiche)
from .docker_connector import DockerConnector
# Connettore reale per processi locali dedicati (HTTP server standalone su porte TCP)
from .process_connector import ProcessConnector

# Mappa globale (Service Locator) che associa l'ID univoco all'istanza del connettore
REGISTRY: Dict[str, BaseConnector] = {
    "docker-connector": DockerConnector(),
    "process-connector": ProcessConnector(),
    "cloud-adapter": CloudAdapter(),
    "database-adapter": DatabaseAdapter(),
    "k8s-adapter": KubernetesAdapter(),
    "saas-adapter": SaaSAdapter(),
}


def get_connector(connector_id: str) -> Optional[BaseConnector]:
    """
    Recupera l'istanza del connettore registrato corrispondente all'ID specificato.
    Restituisce None se il connettore non è censito nel registry.
    """
    return REGISTRY.get(connector_id)
