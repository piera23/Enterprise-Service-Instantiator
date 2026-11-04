import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..models import (
    ProvisionRequest,
    Instance,
    InstanceStatus,
    ActionRequest
)
from .storage import (
    upsert_instance,
    get_instance_by_id,
    remove_instance,
    get_blueprint_by_id_from_db as get_blueprint_by_id,
    log_audit
)
from .policy_engine import PolicyEngine


class Orchestrator:
    @staticmethod
    def create_instance_entry(request: ProvisionRequest) -> Instance:
        blueprint = get_blueprint_by_id(request.blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint '{request.blueprint_id}' non trovato")

        connector = get_connector(blueprint.connector_id)
        if not connector:
            raise ValueError(f"Connettore '{blueprint.connector_id}' non disponibile")

        is_valid, validation_msg = connector.validate_parameters(request.parameters)
        if not is_valid:
            raise ValueError(f"Validazione parametri fallita: {validation_msg}")

        cost = connector.calculate_cost(blueprint.base_monthly_cost, request.parameters)
        allowed, initial_status, policy_msg = PolicyEngine.evaluate(blueprint, request, cost)

        instance_id = f"inst-{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        expires_at = now + timedelta(days=request.ttl_days)

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

        upsert_instance(instance)
        return instance

    @staticmethod
    async def start_provisioning(instance_id: str):
        instance = get_instance_by_id(instance_id)
        if not instance:
            return

        if instance.status == InstanceStatus.APPROVAL_REQUIRED:
            return  # In attesa di approvazione manuale

        blueprint = get_blueprint_by_id(instance.blueprint_id)
        connector = get_connector(blueprint.connector_id)

        instance.status = InstanceStatus.PROVISIONING
        instance.progress_percentage = 5
        instance.progress_message = "Avvio orchestratore connettore..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Avvio provisioning con {connector.name}")
        upsert_instance(instance)

        async def on_progress(pct: int, msg: str):
            curr = get_instance_by_id(instance_id)
            if curr:
                curr.progress_percentage = pct
                curr.progress_message = msg
                curr.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ({pct}%) {msg}")
                upsert_instance(curr)

        try:
            result = await connector.apply_provisioning(
                instance_id=instance.id,
                name=instance.name,
                parameters=instance.parameters,
                progress_callback=on_progress
            )

            # Completato con successo
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
            curr = get_instance_by_id(instance_id)
            if curr:
                curr.status = InstanceStatus.FAILED
                curr.progress_message = f"Errore durante il provisioning: {str(e)}"
                curr.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERRORE: {str(e)}")
                upsert_instance(curr)

    @staticmethod
    async def approve_instance(instance_id: str) -> Optional[Instance]:
        instance = get_instance_by_id(instance_id)
        if not instance:
            return None

        instance.status = InstanceStatus.PENDING
        instance.progress_message = "Autorizzazione approvata dal responsabile. Avvio in coda..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Richiesta approvata con successo.")
        upsert_instance(instance)

        asyncio.create_task(Orchestrator.start_provisioning(instance_id))
        return instance

    @staticmethod
    async def execute_action(instance_id: str, request: ActionRequest) -> Dict[str, Any]:
        instance = get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Istanza {instance_id} non trovata")

        blueprint = get_blueprint_by_id(instance.blueprint_id)
        connector = get_connector(blueprint.connector_id)

        # Gestione estensione TTL
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

        prev_status = instance.status
        instance.status = InstanceStatus.ACTION_IN_PROGRESS
        instance.progress_message = f"Esecuzione operazione '{request.action}' in corso..."
        instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Richiesta azione Day-2: {request.action}")
        upsert_instance(instance)

        try:
            result = await connector.execute_action(instance_id, request.action, request.parameters)
            instance.status = InstanceStatus.STOPPED if request.action == "stop" else InstanceStatus.ACTIVE
            instance.progress_message = result.get("message", "Operazione completata")
            instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Azione {request.action} completata con successo.")
            upsert_instance(instance)
            return result
        except Exception as e:
            instance.status = prev_status
            instance.progress_message = f"Fallimento azione {request.action}: {str(e)}"
            instance.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Errore azione: {str(e)}")
            upsert_instance(instance)
            raise e

    @staticmethod
    async def terminate_instance(instance_id: str) -> bool:
        instance = get_instance_by_id(instance_id)
        if not instance:
            return False

        blueprint = get_blueprint_by_id(instance.blueprint_id)
        if blueprint:
            connector = get_connector(blueprint.connector_id)
            if connector:
                await connector.destroy(instance_id)

        return remove_instance(instance_id)
