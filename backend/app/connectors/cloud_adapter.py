import asyncio
import uuid
from typing import Dict, Any, Tuple
from .base import BaseConnector


class CloudAdapter(BaseConnector):
    id = "cloud-adapter"
    name = "Cloud Infrastructure Connector"
    platform_type = "cloud"
    description = "Interfaccia per Cloud Provider (AWS / Azure / GCP) tramite OpenTofu / Terraform"

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        if "customer_name" not in parameters or not str(parameters["customer_name"]).strip():
            return False, "Il nome del cliente è obbligatorio"
        return True, "Parametri validi"

    def calculate_cost(self, base_cost: float, parameters: Dict[str, Any]) -> float:
        cost = base_cost
        if parameters.get("demo_profile") == "enterprise":
            cost *= 1.6
        return round(cost, 2)

    async def apply_provisioning(
        self,
        instance_id: str,
        name: str,
        parameters: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        customer = parameters.get("customer_name", "cliente").lower().replace(" ", "-")

        steps = [
            (25, "Inizializzazione Virtual Private Cloud e Subnet sicura..."),
            (50, "Creazione Virtual Machine ottimizzata con dischi crittografati..."),
            (75, "Provisioning certificato SSL e registrazione DNS su Cloudflare..."),
            (100, "Ambiente demo configurato e pronto per l'accesso!")
        ]

        for pct, msg in steps:
            await asyncio.sleep(1.8)
            if progress_callback:
                await progress_callback(pct, msg)

        subdomain = f"{slug}-{customer}.demo.internal.company.com"
        temp_pass = f"Demo_{uuid.uuid4().hex[:8].upper()}!"

        return {
            "endpoints": {
                "Portale Web Demo": f"https://{subdomain}",
                "Dashboard Amministrazione": f"https://{subdomain}/admin",
            },
            "credentials": {
                "Username": f"demo-manager@{customer}.com",
                "Password Temporanea": temp_pass
            },
            "metadata": {
                "ip_address": "10.240.12.84",
                "ssl_status": "Valid (Let's Encrypt Enterprise)",
                "region": parameters.get("region", "eu-central-milan")
            }
        }

    async def execute_action(
        self,
        instance_id: str,
        action: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        await asyncio.sleep(1.5)
        if action == "restart":
            return {"status": "SUCCESS", "message": "Macchina virtuale e servizi web riavviati con successo."}
        elif action == "stop":
            return {"status": "SUCCESS", "message": "Macchina virtuale arrestata. Nessun addebito compute attivo."}
        elif action == "start":
            return {"status": "SUCCESS", "message": "Macchina virtuale avviata ed endpoint ripristinati."}
        return {"status": "SUCCESS", "message": f"Azione {action} eseguita."}

    async def destroy(self, instance_id: str) -> bool:
        await asyncio.sleep(1.2)
        return True
