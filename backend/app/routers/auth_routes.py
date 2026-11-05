# ==============================================================================
# ROUTERS/AUTH_ROUTES.PY - Router API Autenticazione, Sessioni JWT e 2FA TOTP
# Gestisce registrazione, login a due fattori (RFC 6238), setup QR e profilo /me
# ==============================================================================

# Costruttori di rotte, dependency injection, gestione eccezioni e codici HTTP
from fastapi import APIRouter, Depends, HTTPException, status
# Sessione del database relazionale SQLAlchemy
from sqlalchemy.orm import Session
# Modello per la validazione dei payload delle richieste
from pydantic import BaseModel
# Tipizzazione Python
from typing import Optional, Dict, Any

# Dependency injection per la sessione DB
from ..database import get_db
# Modello utente nel database
from ..db_models import User
# Funzioni crittografiche, JWT e 2FA TOTP
from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_2fa_secret,
    get_2fa_provisioning_uri,
    verify_2fa_code,
    get_current_user
)

# Istanziazione del router con prefisso di percorso e tag OpenAPI
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & 2FA"])


# ------------------------------------------------------------------------------
# SCHEMI PAYLOAD RICHIESTE HTTP
# ------------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Payload per la registrazione di un nuovo utente aziendale."""
    username: str
    email: str
    password: str
    role: Optional[str] = "developer"  # admin, devops_lead, developer, auditor


class LoginRequest(BaseModel):
    """Payload per il primo passo del login (credenziali email e password)."""
    email: str
    password: str


class Verify2FARequest(BaseModel):
    """Payload per il secondo passo del login (verifica codice TOTP a 6 cifre)."""
    email: str
    session_token: str
    code: str


class Enable2FARequest(BaseModel):
    """Payload per la conferma e abilitazione definitiva del 2FA sull'account."""
    secret: str
    code: str


# ------------------------------------------------------------------------------
# ENDPOINT DI AUTENTICAZIONE E REGISTRAZIONE
# ------------------------------------------------------------------------------

@router.post("/register", summary="Registrazione nuovo utente")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registra un nuovo account utente nel database aziendale.
    Verifica che non esistano duplicati per email o username prima di eseguire l'hashing della password.
    """
    existing = db.query(User).filter((User.email == req.email) | (User.username == req.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email o Username già registrati nel sistema.")

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role or "developer",
        is_2fa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"status": "SUCCESS", "message": "Utente registrato con successo. Ora puoi effettuare il login."}


@router.post("/login", summary="Login utente (Passo 1: Password)")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Fase 1 dell'autenticazione:
    - Se l'utente non ha il 2FA abilitato: emette direttamente il token Bearer JWT finale.
    - Se l'utente ha il 2FA abilitato: emette un token temporaneo con scope '2fa_pending'
      e richiede il codice numerico a 6 cifre dall'app Authenticator.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o password non corretti.")

    # Se l'utente ha il 2FA abilitato, richiediamo il codice TOTP prima del token finale
    if user.is_2fa_enabled and user.totp_secret:
        temp_token = create_access_token(
            {"sub": user.email, "scope": "2fa_pending"},
            expires_delta=None
        )
        return {
            "requires_2fa": True,
            "session_token": temp_token,
            "message": "Autenticazione a due fattori (2FA) richiesta. Inserisci il codice a 6 cifre dall'app Authenticator."
        }

    # Login standard senza 2FA
    access_token = create_access_token({"sub": user.email, "role": user.role, "name": user.username})
    return {
        "requires_2fa": False,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_2fa_enabled": user.is_2fa_enabled
        }
    }


@router.post("/verify-2fa", summary="Verifica 2FA TOTP (Passo 2: Codice a 6 cifre)")
def verify_2fa(req: Verify2FARequest, db: Session = Depends(get_db)):
    """
    Fase 2 dell'autenticazione a due fattori:
    Valida il token provvisorio della sessione e confronta il codice TOTP inserito
    con l'algoritmo RFC 6238. Se corretto, restituisce il token JWT Bearer definitivo.
    """
    payload = decode_access_token(req.session_token)
    if not payload or payload.get("scope") != "2fa_pending" or payload.get("sub") != req.email:
        raise HTTPException(status_code=401, detail="Sessione 2FA non valida o scaduta. Riprova il login.")

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Configurazione 2FA non trovata per questo account.")

    # Verifica crittografica del codice temporale TOTP
    if not verify_2fa_code(user.totp_secret, req.code):
        raise HTTPException(status_code=401, detail="Codice 2FA non valido o scaduto.")

    # 2FA superato con successo -> emissione del token finale con privilegi completi
    access_token = create_access_token({"sub": user.email, "role": user.role, "name": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_2fa_enabled": True
        }
    }


# ------------------------------------------------------------------------------
# CONFIGURAZIONE E GESTIONE 2FA PER L'UTENTE COLLEGATO
# ------------------------------------------------------------------------------

@router.get("/2fa/setup", summary="Genera chiave segreta e URI per configurare Google/Microsoft Authenticator")
def setup_2fa(current_user: User = Depends(get_current_user)):
    """
    Genera una nuova chiave segreta Base32 e l'URI standard otpauth://
    per consentire all'utente di aggiungere il token alla propria app di autenticazione.
    """
    secret = generate_2fa_secret()
    uri = get_2fa_provisioning_uri(secret, current_user.email)
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "instructions": "Inserisci la chiave segreta nella tua app Authenticator (Google Authenticator, Microsoft Authenticator o Authy) o usa l'URI per generare il codice."
    }


@router.post("/2fa/enable", summary="Verifica e abilita definitivamente il 2FA sull'account")
def enable_2fa(req: Enable2FARequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Richiede all'utente di inserire il primo codice a 6 cifre per validare che la sincronizzazione
    con l'app Authenticator sia riuscita prima di attivare definitivamente l'obbligo del 2FA.
    """
    if not verify_2fa_code(req.secret, req.code):
        raise HTTPException(status_code=400, detail="Codice TOTP non valido. Verifica l'orario del tuo dispositivo e riprova.")

    current_user.totp_secret = req.secret
    current_user.is_2fa_enabled = True
    db.commit()
    return {"status": "SUCCESS", "message": "Autenticazione a due fattori (2FA) abilitata con successo sul tuo account!"}


@router.post("/2fa/disable", summary="Disabilita 2FA")
def disable_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disabilita l'autenticazione a due fattori e rimuove la chiave segreta dell'utente."""
    current_user.totp_secret = None
    current_user.is_2fa_enabled = False
    db.commit()
    return {"status": "SUCCESS", "message": "2FA disabilitato."}


@router.get("/me", summary="Profilo utente corrente")
def get_me(current_user: User = Depends(get_current_user)):
    """Restituisce le informazioni del profilo dell'utente attualmente autenticato."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }
