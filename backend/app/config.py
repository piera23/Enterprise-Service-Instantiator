# ==============================================================================
# CONFIG.PY - Configurazione dei Percorsi e Risorse del Progetto
# Definisce le directory radice per dati persistenti e file statici frontend
# ==============================================================================

# Modulo del sistema operativo per l'accesso all'ambiente e ai percorsi
import os
# Classe Path della libreria standard pathlib per una gestione cross-platform dei percorsi
from pathlib import Path

# Percorso assoluto della cartella 'backend' (due livelli sopra questo file config.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Cartella dedicata alla persistenza dei dati (database locale SQLite, file json, log)
DATA_DIR = BASE_DIR / "data"

# Cartella contenente l'applicazione Single Page Application (HTML, CSS, JS) del frontend
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Assicura che la directory dei dati esista; se non esiste la crea ricorsivamente
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Percorso del file JSON utilizzato per memorizzazione delle istanze (legacy o backup rapido)
INSTANCES_FILE = DATA_DIR / "instances.json"
