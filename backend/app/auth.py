import os
import hashlib
import secrets
import pyotp
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import get_db
from .db_models import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "esi-super-secret-jwt-key-2026-enterprise-grade")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 ore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, key_hex = hashed_password.split(":")
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# 2FA (TOTP) Helpers
def generate_2fa_secret() -> str:
    return pyotp.random_base32()


def get_2fa_provisioning_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="Enterprise Service Instantiator")


def verify_2fa_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# Dependency: utente corrente autenticato
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali di accesso non valide o sessione scaduta",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # Se non c'è token, restituisce None o lancia eccezione
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_email: str = payload.get("sub")
    if user_email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operazione riservata ai ruoli: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
