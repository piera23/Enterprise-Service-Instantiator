# ==============================================================================
# TEST_AUTH_2FA_POSTGRES.PY - Test di Integrazione e Sicurezza
# Verifica l'hashing password, token JWT Bearer, 2FA TOTP e persistenza SQLAlchemy
# ==============================================================================

# Modulo di sistema per manipolare il sys.path di importazione
import sys
# Supporto per chiamate e test asincroni
import asyncio
# Libreria per generare e convalidare codici TOTP RFC 6238
import pyotp
# Gestione dei percorsi file system in modo cross-platform
from pathlib import Path

# Setup del path: aggiunge la cartella 'backend' a sys.path per importare i moduli interni
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

# Importazione della sessione e dei metadata del database
from app.database import SessionLocal, engine, Base
# Importazione dei modelli ORM delle tabelle
from app.db_models import User, InstanceRecord
# Funzioni crittografiche, JWT e TOTP da testare
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_2fa_secret,
    verify_2fa_code
)
# Schemi Pydantic per provisioning e ambienti
from app.models import ProvisionRequest, EnvironmentEnum
# Orchestratore per la creazione di istanze
from app.services.orchestrator import Orchestrator
# Funzioni per il recupero e gestione delle istanze da database
from app.services.storage import get_all_instances, get_instance_by_id


def test_auth_and_2fa():
    """
    Test suite per verificare:
    1. Hashing PBKDF2-SHA256 con sale e verifica password positiva/negativa
    2. Creazione, firma e decodifica dei token JWT Bearer con claims
    3. Generazione e validazione dei codici temporali TOTP (Google Authenticator)
    """
    print("=" * 60)
    print("TEST: Autenticazione Sicura, Password Hashing e 2FA TOTP")
    print("=" * 60)

    # 1. Test di verifica dell'hashing sicuro delle password
    pwd = "EnterpriseSecurePass2026!"
    hashed = hash_password(pwd)
    # Assicura che la password corretta superi la verifica
    assert verify_password(pwd, hashed), "Password verification failed"
    # Assicura che una password errata venga respinta
    assert not verify_password("WrongPass", hashed), "Wrong password should fail"
    print("[1] Password hashing (PBKDF2 SHA-256 + Salt) verificato OK!")

    # 2. Test del ciclo di vita dei token di accesso JWT
    token = create_access_token({"sub": "admin@azienda.com", "role": "admin"})
    payload = decode_access_token(token)
    # Verifica che il subject contenga l'indirizzo email dell'utente
    assert payload["sub"] == "admin@azienda.com"
    print("[2] Generazione e decodifica JWT Bearer verificata OK!")

    # 3. Test dell'autenticazione a due fattori TOTP (RFC 6238)
    secret = generate_2fa_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    # Verifica che il codice attuale a 6 cifre sia valido
    assert verify_2fa_code(secret, current_code), "TOTP verification failed"
    # Verifica che un codice fittizio o errato venga scartato
    assert not verify_2fa_code(secret, "000000"), "Invalid TOTP should fail"
    print(f"[3] 2FA TOTP (Google Authenticator compatibile): Secret {secret[:8]}... - Codice generato {current_code} verificato OK!")


def test_database_persistence():
    """
    Test suite per verificare:
    4. Connessione e lettura degli utenti dal database SQLAlchemy (PostgreSQL / SQLite)
    5. Creazione di una nuova istanza tramite l'Orchestrator
    6. Persistenza e recupero dei dati dell'istanza salvata
    7. Pulizia della risorsa di test
    """
    print("=" * 60)
    print("TEST: Persistenza Database SQLAlchemy (PostgreSQL / SQLite)")
    print("=" * 60)

    # Apertura di una sessione di database
    db = SessionLocal()
    try:
        # Recupero di tutti gli utenti di seed memorizzati
        users = db.query(User).all()
        print(f"[4] Utenti presenti nel database: {len(users)}")
        for u in users:
            print(f"    -> Utente: {u.username} ({u.email}), Ruolo: {u.role}, 2FA: {u.is_2fa_enabled}")

        # Creazione di una richiesta di provisioning di test
        req = ProvisionRequest(
            blueprint_id="fastapi-microservice",
            name="payment-service-api",
            owner_name="DevOps Lead",
            owner_email="admin@azienda.com",
            team="Core FinTech",
            cost_center="CC-FIN-01",
            environment=EnvironmentEnum.DEV,
            ttl_days=14,
            parameters={"customer_name": "Acme Payments"}
        )
        # Inoltro della richiesta all'orchestratore
        inst = Orchestrator.create_instance_entry(req)
        print(f"[5] Nuova istanza creata nel database: ID {inst.id}, Nome: {inst.name}")

        # Recupero dell'istanza appena salvata nel database
        retrieved = get_instance_by_id(inst.id)
        assert retrieved is not None, "Istanza non trovata nel database!"
        assert retrieved.name == "payment-service-api"
        print(f"[6] Recupero istanza dal database: OK (Nome: {retrieved.name}, Status: {retrieved.status})")

        # Pulizia dell'istanza creata per mantenere il database pulito
        from app.services.storage import remove_instance
        remove_instance(inst.id)
        print("[7] Pulizia istanza di test completata.")
    finally:
        # Chiusura della sessione del database
        db.close()


# Entry point di esecuzione dei test
if __name__ == "__main__":
    test_auth_and_2fa()
    test_database_persistence()
    print("=" * 60)
    print("TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("=" * 60)
