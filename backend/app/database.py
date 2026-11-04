import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://esi_admin:esi_secure_pass123@localhost:5432/esi_database"
)

# Se postgres non è raggiungibile in locale durante sviluppo standalone, fallback pulito su SQLite locale
is_postgres = DATABASE_URL.startswith("postgresql")

try:
    if is_postgres:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        # Test rapido di connessione
        with engine.connect() as conn:
            pass
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
except Exception:
    # Fallback su SQLite locale per sviluppo senza container postgres attivo
    sqlite_path = Path(__file__).resolve().parent.parent / "data" / "esi_database.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
