# ==============================================================================
# MAIN.PY - Applicazione Principale FastAPI
# Configura middleware CORS, routing modulare, lifecycle di startup e file statici
# ==============================================================================

# Modulo di sistema per verificare variabili ed esistenza di directory
import os
# Gestione dei percorsi file system per i file statici del frontend
from pathlib import Path
# Costruttore dell'applicazione FastAPI
from fastapi import FastAPI
# Middleware per consentire richieste Cross-Origin Resource Sharing (CORS)
from fastapi.middleware.cors import CORSMiddleware
# Helper per servire cartelle di asset statici (HTML, CSS, JS, icone)
from fastapi.staticfiles import StaticFiles
# Risposta HTTP specializzata nell'invio diretto di file dal disco
from fastapi.responses import FileResponse

# Percorso della directory del frontend configurato in config.py
from .config import FRONTEND_DIR
# Importazione di tutti i moduli router per le API RESTful
from .routers import catalog, instances, connectors, stats, auth_routes, backoffice
# Modulo storage per l'inizializzazione del database all'avvio
from .services import storage

# Inizializzazione dell'applicazione FastAPI con metadati per la documentazione Swagger / OpenAPI
app = FastAPI(
    title="Enterprise Service Instantiator Platform",
    description=(
        "Piattaforma Enterprise per DevOps & Platform Engineering: "
        "Autenticazione sicura JWT con 2FA (TOTP), persistenza PostgreSQL "
        "e orchestrazione reale di container Docker, database e microservizi."
    ),
    version="2.1.0",
    docs_url="/docs",      # URL dell'interfaccia interattiva Swagger UI
    redoc_url="/redoc"     # URL della documentazione alternativa ReDoc
)

# Configurazione del middleware CORS per consentire connessioni dal browser o da altri host
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Consente qualsiasi origine (adatto ad ambienti aziendali e dev)
    allow_credentials=True,     # Permette l'invio di cookie e header di autorizzazione
    allow_methods=["*"],        # Consente tutti i metodi HTTP (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],        # Consente tutti gli header HTTP personalizzati
)

# Registrazione di tutti i router API con i rispettivi prefissi e tag
app.include_router(auth_routes.router)   # Autenticazione, Registrazione, Login e 2FA TOTP
app.include_router(backoffice.router)    # IAM, Gestione Utenti, Team e Blueprint Studio
app.include_router(catalog.router)       # Catalogo dei servizi e schemi parametri blueprint
app.include_router(instances.router)     # Ciclo di vita delle istanze, ping, azioni Day-2
app.include_router(connectors.router)    # Monitoraggio salute dei connettori di backend
app.include_router(stats.router)         # Cruscotto FinOps e analytics sui costi/risparmi


@app.on_event("startup")
def on_startup():
    """
    Hook di startup eseguito all'avvio del server FastAPI:
    Inizializza le tabelle del database e crea i record di seed (organizzazione, team, utenti e template)
    se non sono già presenti.
    """
    storage.init_db_seeds()


# Configurazione per servire l'interfaccia Web utente (Single Page Application)
if FRONTEND_DIR.exists():
    # Monta la cartella frontend sulla route /static per servire file ausiliari
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", summary="Serve l'interfaccia utente web principale")
    def serve_frontend_index():
        """Restituisce il file index.html dell'interfaccia utente se presente sul disco."""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        # Se index.html non è presente, fornisce una risposta JSON con il link alla documentazione Swagger
        return {"status": "Frontend non trovato", "api_docs": "/docs"}
