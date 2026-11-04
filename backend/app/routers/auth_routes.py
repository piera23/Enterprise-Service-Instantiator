from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..database import get_db
from ..db_models import User
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

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & 2FA"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "developer"  # admin, devops, developer, manager


class LoginRequest(BaseModel):
    email: str
    password: str


class Verify2FARequest(BaseModel):
    email: str
    session_token: str
    code: str


class Enable2FARequest(BaseModel):
    secret: str
    code: str


@router.post("/register", summary="Registrazione nuovo utente")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
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
    payload = decode_access_token(req.session_token)
    if not payload or payload.get("scope") != "2fa_pending" or payload.get("sub") != req.email:
        raise HTTPException(status_code=401, detail="Sessione 2FA non valida o scaduta. Riprova il login.")

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Configurazione 2FA non trovata per questo account.")

    if not verify_2fa_code(user.totp_secret, req.code):
        raise HTTPException(status_code=401, detail="Codice 2FA non valido o scaduto.")

    # 2FA superato con successo -> emetti token finale
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


@router.get("/2fa/setup", summary="Genera chiave segreta e URI per configurare Google/Microsoft Authenticator")
def setup_2fa(current_user: User = Depends(get_current_user)):
    secret = generate_2fa_secret()
    uri = get_2fa_provisioning_uri(secret, current_user.email)
    return {
        "secret": secret,
        "provisioning_uri": uri,
        "instructions": "Inserisci la chiave segreta nella tua app Authenticator (Google Authenticator, Microsoft Authenticator o Authy) o usa l'URI per generare il codice."
    }


@router.post("/2fa/enable", summary="Verifica e abilita definitivamente il 2FA sull'account")
def enable_2fa(req: Enable2FARequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_2fa_code(req.secret, req.code):
        raise HTTPException(status_code=400, detail="Codice TOTP non valido. Verifica l'orario del tuo dispositivo e riprova.")

    current_user.totp_secret = req.secret
    current_user.is_2fa_enabled = True
    db.commit()
    return {"status": "SUCCESS", "message": "Autenticazione a due fattori (2FA) abilitata con successo sul tuo account!"}


@router.post("/2fa/disable", summary="Disabilita 2FA")
def disable_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.totp_secret = None
    current_user.is_2fa_enabled = False
    db.commit()
    return {"status": "SUCCESS", "message": "2FA disabilitato."}


@router.get("/me", summary="Profilo utente corrente")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }
