from fastapi import APIRouter
from typing import List
from ..models import ConnectorInfo
from ..connectors import REGISTRY
from ..services.storage import get_all_instances

router = APIRouter(prefix="/api/v1/connectors", tags=["Connectors"])


@router.get("", response_model=List[ConnectorInfo], summary="Elenco e stato di salute dei connettori registrati")
def list_connectors():
    """Ritorna lo stato delle piattaforme collegate e il numero di risorse attive gestite da ciascuna."""
    all_instances = get_all_instances()
    blueprint_map = {
        "demo-environment": "cloud-adapter",
        "postgres-cluster": "database-adapter",
        "k8s-microservice": "k8s-adapter",
        "saas-workspace": "saas-adapter"
    }

    results = []
    for cid, conn in REGISTRY.items():
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
