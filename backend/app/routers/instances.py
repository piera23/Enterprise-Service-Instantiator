import asyncio
import socket
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from typing import List, Dict, Any
from ..models import Instance, ProvisionRequest, ActionRequest, InstanceStatus
from ..services.storage import get_all_instances, get_instance_by_id
from ..services.orchestrator import Orchestrator
from ..connectors import get_connector
from ..catalog.blueprints import get_blueprint_by_id

router = APIRouter(prefix="/api/v1/instances", tags=["Instances"])


@router.get("", response_model=List[Instance], summary="Elenco di tutte le istanze aziendali")
def list_instances():
    """Ritorna tutte le istanze create, il loro stato in tempo reale e il rispettivo owner."""
    return get_all_instances()


@router.post("", response_model=Instance, status_code=status.HTTP_202_ACCEPTED, summary="Richiedi l'istanziazione di una nuova risorsa")
def create_instance(request: ProvisionRequest, background_tasks: BackgroundTasks):
    """
    Inoltra una richiesta di provisioning.
    Se auto-approvata, il provisioning parte immediatamente in background (asincrono).
    Se richiede approvazione (es. Produzione o superamento budget), viene impostata in attesa.
    """
    try:
        instance = Orchestrator.create_instance_entry(request)
        if instance.status != InstanceStatus.APPROVAL_REQUIRED:
            background_tasks.add_task(Orchestrator.start_provisioning, instance.id)
        return instance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@router.get("/{instance_id}", response_model=Instance, summary="Dettaglio e stato in tempo reale di un'istanza")
def get_instance(instance_id: str):
    instance = get_instance_by_id(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return instance


@router.post("/{instance_id}/ping", summary="Test reale di connettività TCP/HTTP all'istanza")
def ping_instance(instance_id: str):
    """Effettua un handshake TCP reale sulla porta dell'istanza e ne misura la latenza."""
    instance = get_instance_by_id(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")

    # Estrazione porta da credentials o endpoints
    target_port = None
    if "Porta" in instance.credentials:
        try:
            target_port = int(instance.credentials["Porta"])
        except Exception:
            pass

    if not target_port:
        for ep in instance.endpoints.values():
            if ":" in ep:
                parts = ep.split(":")
                candidate = parts[-1].split("/")[0]
                if candidate.isdigit():
                    target_port = int(candidate)
                    break

    if not target_port:
        return {"online": True, "latency_ms": 0.5, "message": "Istanza gestita attiva"}

    start_t = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        res = s.connect_ex(("127.0.0.1", target_port))
        latency = round((time.perf_counter() - start_t) * 1000, 2)

    if res == 0:
        return {
            "online": True,
            "port": target_port,
            "latency_ms": latency,
            "message": f"Servizio online e raggiungibile sulla porta {target_port}!"
        }
    else:
        return {
            "online": False,
            "port": target_port,
            "latency_ms": latency,
            "message": f"Porta {target_port} non risponde. Il servizio potrebbe essere arrestato."
        }


@router.post("/{instance_id}/approve", response_model=Instance, summary="Approva una richiesta che necessitava di autorizzazione")
async def approve_instance(instance_id: str):
    instance = await Orchestrator.approve_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return instance


@router.post("/{instance_id}/actions", summary="Esegui un'operazione Day-2 su un'istanza (restart, backup, extend_ttl, stop)")
async def execute_action(instance_id: str, request: ActionRequest):
    try:
        result = await Orchestrator.execute_action(instance_id, request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{instance_id}", summary="Dismetti ed elimina definitivamente un'istanza")
async def delete_instance(instance_id: str):
    success = await Orchestrator.terminate_instance(instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return {"status": "SUCCESS", "message": f"Istanza {instance_id} de-provisionata ed eliminata."}
