# ==============================================================================
# RUN.PY - Entrypoint di Avvio dell'Applicazione Enterprise Service Instantiator
# Gestisce l'inizializzazione dell'ambiente, il server ASGI Uvicorn e il debugger debugpy
# ==============================================================================

# Server ASGI asincrono ad alte prestazioni per eseguire applicazioni FastAPI / Starlette
import uvicorn
# Modulo standard per interagire con le variabili d'ambiente e il file system del sistema operativo
import os
# Modulo di sistema per configurare percorsi, interprete e flussi standard di I/O
import sys

# Se l'applicazione viene eseguita su ambiente Windows, imposta la codifica della console su UTF-8
# Questo evita problemi con caratteri speciali ed emoji nei log della console Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Calcola il percorso assoluto della cartella 'backend' contenente questo script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Inserisce la cartella backend all'inizio di sys.path per consentire import relativi come 'app.main'
sys.path.insert(0, BASE_DIR)

# Verifica se la modalità di debug è richiesta tramite la variabile d'ambiente DEBUG_MODE
# Accetta valori comuni come "true", "1", "yes" (case-insensitive)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

# Se il debug è attivo, avvia il listener debugpy per consentire l'aggancio di IDE come VS Code
if DEBUG_MODE:
    try:
        # Importa la libreria ufficiale di debug remoto Microsoft debugpy
        import debugpy
        # Legge la porta del debugger (default: 5678)
        debugpy_port = int(os.getenv("DEBUG_PORT", "5678"))
        # debugpy si mette in ascolto su tutte le interfacce di rete (0.0.0.0)
        debugpy.listen(("0.0.0.0", debugpy_port))
        print(f"[DEBUGGER ATTIVO] debugpy in ascolto su 0.0.0.0:{debugpy_port}. Puoi agganciare VS Code (F5)!")
    except Exception as e:
        # Notifica un eventuale fallimento dell'avvio del debugger senza bloccare l'esecuzione
        print(f"[DEBUGGER WARNING] Impossibile avviare debugpy: {e}")

# Blocco di esecuzione principale dello script
if __name__ == "__main__":
    # Determina l'host su cui fare il bind: 0.0.0.0 all'interno di Docker o con PostgreSQL, 127.0.0.1 in locale standalone
    host = os.getenv(
        "HOST",
        "0.0.0.0" if os.path.exists("/.dockerenv") or os.getenv("DATABASE_URL", "").startswith("postgresql://") else "127.0.0.1"
    )
    # Porta HTTP su cui risponderà Uvicorn (default aziendale: 8080)
    port = int(os.getenv("PORT", "8080"))
    # Determina se attivare il ricaricamento automatico al salvataggio dei file (hot-reload)
    reload_enabled = os.getenv("RELOAD", "true" if DEBUG_MODE else "false").lower() in ("true", "1")

    # Banner informativo di avvio con i link di accesso rapido
    print("=" * 65)
    print(">> ENTERPRISE SERVICE INSTANTIATOR - PORTALE AZIENDALE")
    print("=" * 65)
    print(f"Interfaccia Web Utente:        http://localhost:{port}")
    print(f"Documentazione API (Swagger):   http://localhost:{port}/docs")
    if DEBUG_MODE:
        print(f"Porta Debugger Remoto (debugpy): 5678")
    print("=" * 65)
    print("Premi Ctrl+C per arrestare il server.\n")

    # Avvio effettivo del server web ASGI Uvicorn specificando l'applicazione FastAPI 'app.main:app'
    uvicorn.run("app.main:app", host=host, port=port, app_dir=BASE_DIR, reload=reload_enabled)
