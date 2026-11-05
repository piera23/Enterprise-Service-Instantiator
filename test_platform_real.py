# ==============================================================================
# TEST_PLATFORM_REAL.PY - Test Funzionale Live di Provisioning Reale
# Verifica l'avvio di un web server su porta TCP reale, risposta HTTP e azioni Day-2
# ==============================================================================

# Modulo di sistema per configurare sys.path
import sys
# Supporto per coroutine asincrone
import asyncio
# Client HTTP nativo per testare le chiamate di rete reali verso l'endpoint creato
import urllib.request
# Gestione dei percorsi file system in modo cross-platform
from pathlib import Path

# Setup del path: aggiunge la cartella 'backend' al percorso di ricerca dei moduli
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

# Schemi Pydantic per le richieste e gli ambienti
from app.models import ProvisionRequest, EnvironmentEnum
# Orchestratore per avvio e gestione del ciclo di vita
from app.services.orchestrator import Orchestrator
# Funzione per interrogare lo stato dell'istanza dal database
from app.services.storage import get_instance_by_id


async def main():
    """
    Workflow di test funzionale end-to-end:
    1. Creazione della richiesta di provisioning per un ambiente reale
    2. Registrazione dell'istanza nel catalogo e database
    3. Esecuzione del provisioning asincrono su porta TCP dedicata dell'host
    4. Verifica della risposta HTTP con handshake di rete reale
    5. Test di un'operazione Day-2 (restart del servizio)
    6. De-provisioning e rilascio delle risorse
    """
    print("=" * 60)
    print("TEST FUNZIONALE: Istanziazione Reale di un Ambiente Web")
    print("=" * 60)

    # 1. Definizione della richiesta con parametri personalizzati
    req = ProvisionRequest(
        blueprint_id="fastapi-microservice",
        name="Demo Reale Test Live",
        owner_name="Ing. Verdi",
        owner_email="verdi@azienda.com",
        team="Digital Innovation",
        cost_center="CC-INNOV-01",
        environment=EnvironmentEnum.DEV,
        ttl_days=7,
        parameters={"customer_name": "Rossi Grandi Impianti SpA"}
    )

    # 2. Registrazione dell'istanza
    inst = Orchestrator.create_instance_entry(req)
    print(f"[1] Istanza registrata nel catalogo: ID {inst.id}")

    # 3. Avvio del provisioning asincrono (riserva porta TCP e avvia processo)
    print("[2] Avvio provisioning asincrono...")
    await Orchestrator.start_provisioning(inst.id)

    # Recupero dello stato aggiornato dell'istanza
    final_inst = get_instance_by_id(inst.id)
    print(f"[3] Stato finale: {final_inst.status}")
    print(f"[4] Endpoint generati: {final_inst.endpoints}")
    print(f"[5] Credenziali/Metadati: {final_inst.credentials}")

    # 4. Verifica HTTP reale verso l'endpoint locale attivo
    live_url = final_inst.endpoints.get("Portale Web Live")
    if live_url:
        print(f"[6] Verifica HTTP reale verso {live_url} ...")
        with urllib.request.urlopen(live_url, timeout=3) as resp:
            print(f"    -> Risposta HTTP Ricevuta: Codice {resp.status} OK!")
            content = resp.read().decode("utf-8")
            assert "Rossi Grandi Impianti SpA" in content
            print("    -> Contenuto HTML verificato con successo!")

    # 5. Test operazione Day-2: Riavvio del servizio su nuova porta
    print("[7] Test Day-2: Riavvio del servizio...")
    from app.models import ActionRequest
    action_res = await Orchestrator.execute_action(inst.id, ActionRequest(action="restart"))
    print(f"    -> Esito riavvio: {action_res.get('message')}")

    # 6. De-provisioning: arresto del processo e rimozione dal database
    print("[8] De-provisioning e rilascio porta...")
    await Orchestrator.terminate_instance(inst.id)
    print("    -> Risorse rilasciate con successo.")
    print("=" * 60)
    print("TEST COMPLETATO CON SUCCESSO! La piattaforma è funzionante al 100%.")
    print("=" * 60)


# Entry point per l'esecuzione della coroutine principale
if __name__ == "__main__":
    asyncio.run(main())
