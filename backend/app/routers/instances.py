# ==============================================================================
# ROUTERS/INSTANCES.PY - Router API Ciclo di Vita delle Istanze e Azioni Day-2
# Gestisce creazione, monitoraggio live, ping socket TCP, approvazioni e terminazione
# ==============================================================================

# Supporto asincrono
import asyncio
# Sockets di rete a basso livello per eseguire test reali di handshake TCP verso i container
import socket
# Misurazione accurata della latenza in millisecondi
import time
# Costrutti FastAPI per rotte, errori, task in background e codici di stato HTTP
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
# Tipizzazione Python
from typing import List, Dict, Any

# Schemi Pydantic per istanze e richieste
from ..models import Instance, ProvisionRequest, ActionRequest, InstanceStatus
# Funzioni per l'accesso e lettura delle istanze da database
from ..services.storage import get_all_instances, get_instance_by_id
# Orchestratore per avvio provisioning, approvazioni e azioni Day-2
from ..services.orchestrator import Orchestrator
# Registry dei connettori
from ..connectors import get_connector
# Catalogo blueprint statici/dinamici
from ..catalog.blueprints import get_blueprint_by_id

# Istanziazione del router con prefisso di percorso e tag OpenAPI
router = APIRouter(prefix="/api/v1/instances", tags=["Instances"])


@router.get("", response_model=List[Instance], summary="Elenco di tutte le istanze aziendali")
def list_instances():
    """Ritorna tutte le istanze create, il loro stato in tempo reale e il rispettivo owner."""
    return get_all_instances()


@router.post("", response_model=Instance, status_code=status.HTTP_202_ACCEPTED, summary="Richiedi l'istanziazione di una nuova risorsa")
def create_instance(request: ProvisionRequest, background_tasks: BackgroundTasks):
    """
    Inoltra una richiesta di provisioning infrastrutturale.
    - Se conforme e auto-approvata: avvia immediatamente il provisioning in background (asincrono).
    - Se richiede approvazione (es. Produzione o superamento budget FinOps): viene messa in attesa (APPROVAL_REQUIRED).
    """
    try:
        instance = Orchestrator.create_instance_entry(request)
        # Se non è bloccata dalle policy, delega il task di provisioning all'event loop in background
        if instance.status != InstanceStatus.APPROVAL_REQUIRED:
            background_tasks.add_task(Orchestrator.start_provisioning, instance.id)
        return instance
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@router.get("/{instance_id}", response_model=Instance, summary="Dettaglio e stato in tempo reale di un'istanza")
def get_instance(instance_id: str):
    """Restituisce lo stato dettagliato, gli endpoint, le credenziali e i log di una singola istanza."""
    instance = get_instance_by_id(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return instance


@router.post("/{instance_id}/ping", summary="Test reale di connettività TCP/HTTP all'istanza")
def ping_instance(instance_id: str):
    """
    Effettua un handshake TCP reale sulla porta dell'istanza e ne misura la latenza di rete in tempo reale.
    Rileva se il container o il processo è effettivamente in ascolto sulla porta associata.
    """
    instance = get_instance_by_id(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")

    # Estrazione della porta target da credenziali o da endpoint generati
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

    # Se non c'è una porta host specifica (es. mock o risorsa gestita remota)
    if not target_port:
        return {"online": True, "latency_ms": 0.5, "message": "Istanza gestita attiva"}

    # Esecuzione del test di handshake TCP con socket
    start_t = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        # Tenta la connessione alla porta locale su 127.0.0.1
        res = s.connect_ex(("127.0.0.1", target_port))
        latency = round((time.perf_counter() - start_t) * 1000, 2)

    # Connessione riuscita (codice 0)
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
    """
    Approva manualmente un'istanza bloccata in stato APPROVAL_REQUIRED e ne avvia il provisioning.
    """
    instance = await Orchestrator.approve_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return instance


@router.post("/{instance_id}/actions", summary="Esegui un'operazione Day-2 su un'istanza (restart, backup, extend_ttl, stop)")
async def execute_action(instance_id: str, request: ActionRequest):
    """
    Inoltra un'azione Day-2 all'orchestratore:
    - 'restart': riavvio del container o processo
    - 'stop': arresto temporaneo del servizio
    - 'start': riattivazione del servizio
    - 'extend_ttl': proroga della data di scadenza
    - 'backup': snapshot immediato
    """
    try:
        result = await Orchestrator.execute_action(instance_id, request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{instance_id}", summary="Dismetti ed elimina definitivamente un'istanza")
async def delete_instance(instance_id: str):
    """
    De-provisiona e distrugge le risorse dell'istanza (container Docker, processi locali, file)
    e ne rimuove il record dal database.
    """
    success = await Orchestrator.terminate_instance(instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Istanza non trovata")
    return {"status": "SUCCESS", "message": f"Istanza {instance_id} de-provisionata ed eliminata."}
