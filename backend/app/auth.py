# ==============================================================================
# AUTH.PY - Gestione Sicurezza, Hashing Password, JWT Bearer e 2FA (TOTP)
# Implementa crittografia PBKDF2-HMAC-SHA256, token JWT con scadenze e 2FA RFC 6238
# ==============================================================================

# Modulo di sistema per leggere la chiave segreta JWT dalle variabili d'ambiente
import os
# Funzioni crittografiche sicure standard (PBKDF2, SHA-256)
import hashlib
# Generatore di numeri e token casuali crittograficamente sicuri per CSPRNG
import secrets
# Libreria per la gestione di Time-based One-Time Password (TOTP) conformi a Google Authenticator
import pyotp
# Libreria per la codifica e decodifica di token JSON Web Token (JWT)
import jwt
# Gestione dei timestamp e delle durate temporali per le scadenze dei token
from datetime import datetime, timedelta
# Tipizzazione Python per opzionali, dizionari e liste
from typing import Optional, Dict, Any, List
# Costrutti FastAPI per la gestione delle dipendenze, errori HTTP e codici di stato
from fastapi import Depends, HTTPException, status
# Schema di sicurezza OAuth2 Password Bearer integrato con la documentazione Swagger UI
from fastapi.security import OAuth2PasswordBearer
# Sessione ORM di SQLAlchemy per interrogare la tabella utenti
from sqlalchemy.orm import Session
# Dependency injection per ottenere la connessione al database
from .database import get_db
# Modello del database dell'utente
from .db_models import User

# Chiave segreta crittografica aziendale usata per firmare i token JWT (configurabile da env)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "esi-super-secret-jwt-key-2026-enterprise-grade")
# Algoritmo di firma simmetrico HMAC con SHA-256
ALGORITHM = "HS256"
# Durata massima di validità del token di accesso: 12 ore
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

# Definizione dello schema OAuth2 Bearer: auto_error=False permette di gestire l'errore manualmente
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """
    Esegue l'hashing sicuro della password utente.
    Utilizza PBKDF2-HMAC-SHA256 con 100.000 iterazioni e un sale casuale a 16 byte esadecimale.
    Restituisce una stringa nel formato sicuro: 'salt:hex_digest'.
    """
    # Genera un sale crittografico univoco di 16 byte (32 caratteri esadecimali)
    salt = secrets.token_hex(16)
    # Calcola l'hash della password con 100.000 iterazioni PBKDF2
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    # Restituisce sale e hash separati dai due punti
    return f"{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se la password in chiaro corrisponde all'hash salvato nel database.
    Utilizza secrets.compare_digest per prevenire attacchi di tipo timing attack.
    """
    try:
        # Estrae il sale e l'hash salvato dividendo la stringa
        salt, key_hex = hashed_password.split(":")
        # Ricalcola l'hash della password fornita usando lo stesso sale
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        # Confronta in tempo costante per impedire attacchi di canale laterale (side-channel)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        # In caso di formato hash non valido o corrotto, restituisce False
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Genera un token di accesso JWT firmato con claims personalizzati e scadenza prefissata.
    """
    # Crea una copia del dizionario di payload per non modificare l'originale
    to_encode = data.copy()
    # Calcola la data e ora di scadenza UTC
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # Inserisce il claim standard 'exp' (expiration time) nel payload del token
    to_encode.update({"exp": expire})
    # Firma e codifica il token JWT tramite la chiave segreta aziendale
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica e verifica l'integrità della firma e la scadenza temporale di un token JWT.
    Restituisce il payload se valido, altrimenti None.
    """
    try:
        # Decodifica il token verificando sia la firma che la data di scadenza
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        # Token scaduto, firma non valida o manomesso
        return None


# ------------------------------------------------------------------------------
# 2FA (TOTP - Time-Based One-Time Password) RFC 6238
# ------------------------------------------------------------------------------

def generate_2fa_secret() -> str:
    """
    Genera una nuova chiave segreta a 32 caratteri codificata in Base32 per configurare il 2FA.
    """
    return pyotp.random_base32()


def get_2fa_provisioning_uri(secret: str, email: str) -> str:
    """
    Genera l'URI di provisioning compatibile con Google Authenticator, Microsoft Authenticator o Authy
    (es. 'otpauth://totp/Enterprise%20Service...').
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="Enterprise Service Instantiator")


def verify_2fa_code(secret: str, code: str) -> bool:
    """
    Verifica la correttezza del codice numerico a 6 cifre inviato dall'utente.
    valid_window=1 consente una tolleranza di 30 secondi prima o dopo per compensare lievi drift di clock.
    """
    if not secret or not code:
        return False
    # Istanzia l'oggetto TOTP associato alla chiave segreta
    totp = pyotp.TOTP(secret)
    # Esegue la verifica del codice con finestra di tolleranza di 1 passo temporale
    return totp.verify(code, valid_window=1)


# ------------------------------------------------------------------------------
# DEPENDENCY INJECTION: Autenticazione e Controllo dei Ruoli (RBAC)
# ------------------------------------------------------------------------------

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency FastAPI che estrae il token Bearer dall'header Authorization,
    lo valida e carica l'utente autenticato corrispondente dal database.
    """
    # Struttura eccezione standard per credenziali non valide o scadute (HTTP 401)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali di accesso non valide o sessione scaduta",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Se la richiesta non include un token nell'header Authorization
    if not token:
        raise credentials_exception

    # Decodifica e validazione crittografica del token JWT
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Estrazione dell'identificativo utente (subject: email)
    user_email: str = payload.get("sub")
    if user_email is None:
        raise credentials_exception

    # Recupero del record utente corrispondente dal database
    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise credentials_exception

    # Restituisce l'oggetto User corrente all'endpoint
    return user


def require_roles(allowed_roles: List[str]):
    """
    Factory per creare dipendenze di autorizzazione RBAC (Role-Based Access Control).
    Consente l'accesso solo agli utenti con un ruolo compreso nella lista 'allowed_roles'.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Se il ruolo dell'utente autenticato non è autorizzato, restituisce errore HTTP 403 Forbidden
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operazione riservata ai ruoli: {', '.join(allowed_roles)}"
            )
        # Utente autorizzato
        return current_user
    return role_checker
