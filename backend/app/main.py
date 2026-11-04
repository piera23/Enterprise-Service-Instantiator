import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import FRONTEND_DIR
from .routers import catalog, instances, connectors, stats, auth_routes, backoffice
from .services import storage

app = FastAPI(
    title="Enterprise Service Instantiator Platform",
    description=(
        "Piattaforma Enterprise per DevOps & Platform Engineering: "
        "Autenticazione sicura JWT con 2FA (TOTP), persistenza PostgreSQL "
        "e orchestrazione reale di container Docker, database e microservizi."
    ),
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS per consentire connessione da frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusione routers
app.include_router(auth_routes.router)
app.include_router(backoffice.router)
app.include_router(catalog.router)
app.include_router(instances.router)
app.include_router(connectors.router)
app.include_router(stats.router)


@app.on_event("startup")
def on_startup():
    storage.init_db_seeds()


# Servire il frontend se presente
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"status": "Frontend non trovato", "api_docs": "/docs"}
