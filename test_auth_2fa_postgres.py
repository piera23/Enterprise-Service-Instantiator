import sys
import asyncio
import pyotp
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.database import SessionLocal, engine, Base
from app.db_models import User, InstanceRecord
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_2fa_secret,
    verify_2fa_code
)
from app.models import ProvisionRequest, EnvironmentEnum
from app.services.orchestrator import Orchestrator
from app.services.storage import get_all_instances, get_instance_by_id


def test_auth_and_2fa():
    print("=" * 60)
    print("TEST: Autenticazione Sicura, Password Hashing e 2FA TOTP")
    print("=" * 60)

    # 1. Password hashing test
    pwd = "EnterpriseSecurePass2026!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed), "Password verification failed"
    assert not verify_password("WrongPass", hashed), "Wrong password should fail"
    print("[1] Password hashing (PBKDF2 SHA-256 + Salt) verificato OK!")

    # 2. JWT Token test
    token = create_access_token({"sub": "admin@azienda.com", "role": "admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == "admin@azienda.com"
    print("[2] Generazione e decodifica JWT Bearer verificata OK!")

    # 3. 2FA TOTP test
    secret = generate_2fa_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert verify_2fa_code(secret, current_code), "TOTP verification failed"
    assert not verify_2fa_code(secret, "000000"), "Invalid TOTP should fail"
    print(f"[3] 2FA TOTP (Google Authenticator compatibile): Secret {secret[:8]}... - Codice generato {current_code} verificato OK!")


def test_database_persistence():
    print("=" * 60)
    print("TEST: Persistenza Database SQLAlchemy (PostgreSQL / SQLite)")
    print("=" * 60)

    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"[4] Utenti presenti nel database: {len(users)}")
        for u in users:
            print(f"    -> Utente: {u.username} ({u.email}), Ruolo: {u.role}, 2FA: {u.is_2fa_enabled}")

        # Provisioning test in DB
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
        inst = Orchestrator.create_instance_entry(req)
        print(f"[5] Nuova istanza creata nel database: ID {inst.id}, Nome: {inst.name}")

        retrieved = get_instance_by_id(inst.id)
        assert retrieved is not None, "Istanza non trovata nel database!"
        assert retrieved.name == "payment-service-api"
        print(f"[6] Recupero istanza dal database: OK (Nome: {retrieved.name}, Status: {retrieved.status})")

        # Cleanup test instance
        from app.services.storage import remove_instance
        remove_instance(inst.id)
        print("[7] Pulizia istanza di test completata.")
    finally:
        db.close()


if __name__ == "__main__":
    test_auth_and_2fa()
    test_database_persistence()
    print("=" * 60)
    print("TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("=" * 60)
