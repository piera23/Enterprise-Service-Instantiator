# ==============================================================================
# ROUTERS/CONNECTORS.PY - Router API per il Monitoraggio dei Connettori di Backend
# Espone endpoint per verificare salute, disponibilità e carico di lavoro dei connettori
# ==============================================================================

# Costruttore del router di FastAPI
from fastapi import APIRouter
# Tipizzazione Python per liste
from typing import List
# Schema informativo per i connettori
from ..models import ConnectorInfo
# Registro centrale contenente tutte le istanze dei connettori
from ..connectors import REGISTRY
# Query per ottenere le istanze correnti e calcolare il carico
from ..services.storage import get_all_instances

# Istanziazione del router con prefisso di percorso e tag OpenAPI
router = APIRouter(prefix="/api/v1/connectors", tags=["Connectors"])


@router.get("", response_model=List[ConnectorInfo], summary="Elenco e stato di salute dei connettori registrati")
def list_connectors():
    """
    Ritorna lo stato delle piattaforme collegate (Docker, Processi, Cloud, Database, K8s, SaaS)
    e calcola il numero di risorse attive gestite da ciascun connettore.
    """
    all_instances = get_all_instances()

    # Mappatura dei blueprint storici sui rispettivi connettori per il conteggio
    blueprint_map = {
        "demo-environment": "cloud-adapter",
        "postgres-cluster": "database-adapter",
        "k8s-microservice": "k8s-adapter",
        "saas-workspace": "saas-adapter"
    }

    results = []
    # Itera su ciascun connettore registrato nel registry globale
    for cid, conn in REGISTRY.items():
        # Conteggia quante istanze sono attualmente associate a questo connettore
        count = sum(1 for inst in all_instances if blueprint_map.get(inst.blueprint_id) == cid)
        results.append(
            ConnectorInfo(
                id=conn.id,
                name=conn.name,
                type=conn.platform_type,
                description=conn.description,
                status="ONLINE",
                active_instances_count=count
            )
        )
    return results
