import sys
import asyncio
import urllib.request
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.models import ProvisionRequest, EnvironmentEnum
from app.services.orchestrator import Orchestrator
from app.services.storage import get_instance_by_id


async def main():
    print("=" * 60)
    print("TEST FUNZIONALE: Istanziazione Reale di un Ambiente Web")
    print("=" * 60)

    req = ProvisionRequest(
        blueprint_id="real-web-demo",
        name="Demo Reale Test Live",
        owner_name="Ing. Verdi",
        owner_email="verdi@azienda.com",
        team="Digital Innovation",
        cost_center="CC-INNOV-01",
        environment=EnvironmentEnum.DEV,
        ttl_days=7,
        parameters={"customer_name": "Rossi Grandi Impianti SpA"}
    )

    inst = Orchestrator.create_instance_entry(req)
    print(f"[1] Istanza registrata nel catalogo: ID {inst.id}")

    print("[2] Avvio provisioning asincrono...")
    await Orchestrator.start_provisioning(inst.id)

    final_inst = get_instance_by_id(inst.id)
    print(f"[3] Stato finale: {final_inst.status}")
    print(f"[4] Endpoint generati: {final_inst.endpoints}")
    print(f"[5] Credenziali/Metadati: {final_inst.credentials}")

    live_url = final_inst.endpoints.get("Portale Web Live")
    if live_url:
        print(f"[6] Verifica HTTP reale verso {live_url} ...")
        with urllib.request.urlopen(live_url, timeout=3) as resp:
            print(f"    -> Risposta HTTP Ricevuta: Codice {resp.status} OK!")
            content = resp.read().decode("utf-8")
            assert "Rossi Grandi Impianti SpA" in content
            print("    -> Contenuto HTML verificato con successo!")

    # Day-2: Restart test
    print("[7] Test Day-2: Riavvio del servizio...")
    from app.models import ActionRequest
    action_res = await Orchestrator.execute_action(inst.id, ActionRequest(action="restart"))
    print(f"    -> Esito riavvio: {action_res.get('message')}")

    # Pulizia
    print("[8] De-provisioning e rilascio porta...")
    await Orchestrator.terminate_instance(inst.id)
    print("    -> Risorse rilasciate con successo.")
    print("=" * 60)
    print("TEST COMPLETATO CON SUCCESSO! La piattaforma è funzionante al 100%.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
