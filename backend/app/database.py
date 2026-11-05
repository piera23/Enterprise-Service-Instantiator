# ==============================================================================
# DATABASE.PY - Configurazione Connessione Database (SQLAlchemy)
# Supporta PostgreSQL enterprise con failover trasparente su SQLite locale
# ==============================================================================

# Modulo di sistema per leggere le variabili d'ambiente
import os
# Gestione dei percorsi file system per il database SQLite di fallback
from pathlib import Path
# Costruttore dell'Engine di connessione del database di SQLAlchemy
from sqlalchemy import create_engine
# Strumenti per la definizione dichiarativa dei modelli e per la gestione delle sessioni
from sqlalchemy.orm import declarative_base, sessionmaker

# Lettura dell'URL di connessione dal file d'ambiente, con default verso il PostgreSQL Docker locale
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://esi_admin:esi_secure_pass123@localhost:5432/esi_database"
)

# Verifica se il protocollo indicato è PostgreSQL
is_postgres = DATABASE_URL.startswith("postgresql")

try:
    if is_postgres:
        # Configurazione dell'engine per PostgreSQL:
        # pool_pre_ping=True verifica la validità delle connessioni nel pool prima di utilizzarle
        # connect_timeout=3 impedisce blocchi prolungati se il database non è ancora pronto
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        # Test rapido di connessione per verificare l'effettiva disponibilità di PostgreSQL
        with engine.connect() as conn:
            pass
    else:
        # Configurazione standard per database non-postgres (es. sqlite già specificato)
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
except Exception:
    # FALLBACK AUTOMATICO SU SQLITE LOCALE:
    # Se il container o il server PostgreSQL non è attivo o raggiungibile,
    # l'applicazione passa istantaneamente e senza crash a un database SQLite locale su file
    sqlite_path = Path(__file__).resolve().parent.parent / "data" / "esi_database.db"
    # Assicura che la directory di destinazione esista
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    # Creazione dell'engine SQLite; check_same_thread=False consente l'uso multi-thread di FastAPI
    engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})

# Creazione della factory per le sessioni del database:
# autocommit=False garantisce la gestione esplicita delle transazioni atomiche
# autoflush=False impedisce flush automatici non voluti prima delle query
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe Base dichiarativa da cui erediteranno tutti i modelli delle tabelle SQLAlchemy
Base = declarative_base()


def get_db():
    """
    Dependency Injection di FastAPI per ottenere una sessione di database per ogni richiesta HTTP.
    Garantisce che la sessione venga chiusa correttamente al termine della richiesta (blocco finally).
    """
    # Apertura di una nuova sessione per la richiesta corrente
    db = SessionLocal()
    try:
        # Fornisce la sessione all'endpoint chiamante
        yield db
    finally:
        # Chiusura e rilascio della connessione al pool al termine dell'operazione
        db.close()
