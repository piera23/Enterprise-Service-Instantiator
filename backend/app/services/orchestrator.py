# ==============================================================================
# ORCHESTRATOR.PY - Motore Centrale di Orchestrazione del Ciclo di Vita
# Coordina la validazione, il motore di policy, l'invocazione dei connettori e le azioni Day-2
# ==============================================================================

# Supporto alle operazioni asincrone e task in background
import asyncio
# Generazione degli ID univoci per le nuove istanze
import uuid
# Calcolo delle scadenze temporali (TTL) tramite datetime e timedelta
from datetime import datetime, timedelta
# Tipizzazione Python per dizionari e valori opzionali
from typing import Dict, Any, Optional

# Schemi Pydantic per richieste, istanze e azioni
from ..models import (
    ProvisionRequest,
    Instance,
    InstanceStatus,
    ActionRequest
)
# Funzioni per la persistenza su database relazionale e audit logging
from .storage import (
    upsert_instance,
    get_instance_by_id,
    remove_instance,
    get_blueprint_by_id_from_db as get_blueprint_by_id,
    log_audit
)
# Motore di valutazione policy aziendali
from .policy_engine import PolicyEngine
# Registry dei connettori di backend per recuperare il driver corretto
from ..connectors import get_connector


class Orchestrator:
    """
    Orchestratore principale del ciclo di vita delle risorse.
    Gestisce la ricezione delle richieste, l'applicazione delle policy di governance,
    il tracciamento dello stato nel database e il dispatching verso i connettori infrastrutturali.
    """

    @staticmethod
    def create_instance_entry(request: ProvisionRequest) -> Instance:
        """
        Crea il record iniziale dell'istanza nel database:
        1. Recupera il blueprint dal catalogo
        2. Individua e valida i parametri con il connettore preposto
        3. Calcola il costo totale mensile
        4. Valuta le policy aziendali (auto-approvazione vs blocco per autorizzazione)
        5. Salva l'istanza con stato iniziale PENDING o APPROVAL_REQUIRED
        """
        # Recupera il blueprint selezionato dal database
        blueprint = get_blueprint_by_id(request.blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint '{request.blueprint_id}' non trovato")

        # Recupera il connettore associato al blueprint
        connector = get_connector(blueprint.connector_id)
        if not connector:
            raise ValueError(f"Connettore '{blueprint.connector_id}' non disponibile")

        # Esegue la validazione dei parametri specifici del connettore
        is_valid, validation_msg = connector.validate_parameters(request.parameters)
        if not is_valid:
            raise ValueError(f"Validazione parametri fallita: {validation_msg}")

        # Calcola il costo mensile totale dell'istanza
        cost = connector.calculate_cost(blueprint.base_monthly_cost, request.parameters)
        # Valuta i guardrails di governance (ambiente, budget, TTL)
        allowed, initial_status, policy_msg = PolicyEngine.evaluate(blueprint, request, cost)

        # Genera un ID univoco per la nuova istanza (es. "inst-4b8c9f1a")
        instance_id = f"inst-{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        # Calcola la data e ora di scadenza in base ai giorni di TTL richiesti
        expires_at = now + timedelta(days=request.ttl_days)

        # Costruisce l'oggetto modello Instance con tutti i dettagli
        instance = Instance(
            id=instance_id,
            blueprint_id=blueprint.id,
            blueprint_title=blueprint.title,
            category=blueprint.category,
            icon=blueprint.icon,
            name=request.name,
            owner_name=request.owner_name,
            owner_email=request.owner_email,
            team=request.team,
            cost_center=request.cost_center,
            environment=request.environment,
            status=initial_status,
            progress_percentage=0 if initial_status != InstanceStatus.APPROVAL_REQUIRED else 0,
            progress_message=policy_msg,
            created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            expires_at=expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            ttl_days=request.ttl_days,
            monthly_cost=cost,
            parameters=request.parameters,
            day2_actions=blueprint.day2_actions,
            logs=[f"[{now.strftime('%H:%M:%S')}] Richiesta ricevuta: {policy_msg}"]
        )

        # Salva o aggiorna l'istanza nel database relazionale
        upsert_instance(instance)
        return instance

    @staticmethod
    async def start_provisioning(instance_id: str):
        """
        Esegue il workflow asincrono di provisioning infrastrutturale.
        Aggiorna costantemente lo stato nel database e gestisce eventuali errori impostando lo stato su FAILED.
        """
        # Recupera l'istanza dal database
        instance = get_instance_by_id(instance_id)
        if not instance:
            return

        # Se l'istanza è bloccata in attesa di approvazione, non avviare il provisioning
        if instance.status == InstanceStatus.APPROVAL_REQUIRED:
            return

        # Recupera il template e il rispettivo connettore
        blueprint = get_blueprint_by_id(instance.blueprint_id)
        connector = get_connector(blueprint.connector_id)

        # Imposta lo stato su PROVISIONING e salva l'evento nei log
        instance.status = InstanceStatus.PROVISIONING
        instance.progress_percentage = 5
        instance.progress_message = "Avvio orchestratore connettore..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Avvio provisioning con {connector.name}")
        upsert_instance(instance)

        # Callback asincrono invocato dal connettore per notificare avanzamento percentuale e messaggi
        async def on_progress(pct: int, msg: str):
            curr = get_instance_by_id(instance_id)
            if curr:
                curr.progress_percentage = pct
                curr.progress_message = msg
                curr.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ({pct}%) {msg}")
                upsert_instance(curr)

        try:
            # Invocazione del connettore infrastrutturale reale o simulato
            result = await connector.apply_provisioning(
                instance_id=instance.id,
                name=instance.name,
                parameters=instance.parameters,
                progress_callback=on_progress
            )

            # Provisioning completato con successo: impostazione dello stato su ACTIVE
            curr = get_instance_by_id(instance_id)
            if curr:
                curr.status = InstanceStatus.ACTIVE
                curr.progress_percentage = 100
                curr.progress_message = "Servizio attivo e pronto all'uso!"
                curr.endpoints = result.get("endpoints", {})
                curr.credentials = result.get("credentials", {})
                curr.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Provisioning completato con successo.")
                upsert_instance(curr)

        except Exception as e:
            # Gestione errore: aggiornamento dello stato su FAILED con dettagli dell'eccezione
            curr = get_instance_by_id(instance_id)
            if curr:
                curr.status = InstanceStatus.FAILED
                curr.progress_message = f"Errore durante il provisioning: {str(e)}"
                curr.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERRORE: {str(e)}")
                upsert_instance(curr)

    @staticmethod
    async def approve_instance(instance_id: str) -> Optional[Instance]:
        """
        Approva manualmente una richiesta in sospeso (APPROVAL_REQUIRED),
        impostandola su PENDING e avviando immediatamente il task asincrono di provisioning.
        """
        instance = get_instance_by_id(instance_id)
        if not instance:
            return None

        instance.status = InstanceStatus.PENDING
        instance.progress_message = "Autorizzazione approvata dal responsabile. Avvio in coda..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Richiesta approvata con successo.")
        upsert_instance(instance)

        # Avvio del task di provisioning in background
        asyncio.create_task(Orchestrator.start_provisioning(instance_id))
        return instance

    @staticmethod
    async def execute_action(instance_id: str, request: ActionRequest) -> Dict[str, Any]:
        """
        Esegue un'operazione Day-2 su una risorsa attiva:
        - Se 'extend_ttl': proroga la data di scadenza dell'istanza
        - Per altre azioni (restart, stop, start, backup): le inoltra al connettore competente
        """
        instance = get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Istanza {instance_id} non trovata")

        blueprint = get_blueprint_by_id(instance.blueprint_id)
        connector = get_connector(blueprint.connector_id)

        # Gestione speciale dell'estensione del TTL (non necessita del connettore)
        if request.action == "extend_ttl":
            days = 7
            if request.parameters and "days" in request.parameters:
                days = int(request.parameters["days"])
            current_expiry = datetime.strptime(instance.expires_at, "%Y-%m-%d %H:%M:%S")
            new_expiry = current_expiry + timedelta(days=days)
            instance.expires_at = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            instance.ttl_days += days
            instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Scadenza prorogata di {days} giorni (fino al {instance.expires_at}).")
            upsert_instance(instance)
            return {"status": "SUCCESS", "message": f"Scadenza prorogata fino al {instance.expires_at}."}

        # Impostazione temporanea dello stato ACTION_IN_PROGRESS
        prev_status = instance.status
        instance.status = InstanceStatus.ACTION_IN_PROGRESS
        instance.progress_message = f"Esecuzione operazione '{request.action}' in corso..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Richiesta azione Day-2: {request.action}")
        upsert_instance(instance)

        try:
            # Esecuzione dell'azione tramite il driver del connettore
            result = await connector.execute_action(instance_id, request.action, request.parameters)
            instance.status = InstanceStatus.STOPPED if request.action == "stop" else InstanceStatus.ACTIVE
            instance.progress_message = result.get("message", "Operazione completata")
            instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Azione {request.action} completata con successo.")
            upsert_instance(instance)
            return result
        except Exception as e:
            # Ripristino dello stato precedente in caso di fallimento
            instance.status = prev_status
            instance.progress_message = f"Fallimento azione {request.action}: {str(e)}"
            instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Errore azione: {str(e)}")
            upsert_instance(instance)
            raise e

    @staticmethod
    async def terminate_instance(instance_id: str) -> bool:
        """
        Dismette ed elimina definitivamente un'istanza:
        1. Invoca il destroy del connettore per arrestare container e processi
        2. Rimuove il record dell'istanza dal database
        """
        instance = get_instance_by_id(instance_id)
        if not instance:
            return False

        blueprint = get_blueprint_by_id(instance.blueprint_id)
        if blueprint:
            connector = get_connector(blueprint.connector_id)
            if connector:
                await connector.destroy(instance_id)

        # Rimozione dal database
        return remove_instance(instance_id)
