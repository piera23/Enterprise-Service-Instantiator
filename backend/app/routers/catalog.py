# ==============================================================================
# ROUTERS/CATALOG.PY - Router API per la Consultazione del Catalogo dei Servizi
# Espone gli endpoint RESTful per visualizzare template e schemi di parametri dinamici
# ==============================================================================

# Costruttore del router e gestione errori HTTP di FastAPI
from fastapi import APIRouter, HTTPException
# Tipizzazione Python per liste
from typing import List
# Schema Pydantic del Blueprint
from ..models import Blueprint
# Query ORM sul database per recuperare i template pubblicati
from ..services.storage import get_all_blueprints_from_db, get_blueprint_by_id_from_db

# Istanziazione del router con prefisso di percorso e tag OpenAPI per la documentazione Swagger
router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


@router.get("/blueprints", response_model=List[Blueprint], summary="Ottieni l'elenco dei blueprint dinamici dal database")
def list_blueprints():
    """
    Ritorna tutti i blueprint attivi e pubblicati memorizzati nel database relazionale.
    Include categorie, badge, icone, costi base e definizioni dei campi di input.
    """
    return get_all_blueprints_from_db()


@router.get("/blueprints/{blueprint_id}", response_model=Blueprint, summary="Dettaglio e schema parametri di un blueprint")
def get_blueprint(blueprint_id: str):
    """
    Ritorna lo schema dettagliato e i parametri dinamici da richiedere all'utente nel form di provisioning.
    Se il blueprint richiesto non esiste nel database, restituisce un errore HTTP 404 Not Found.
    """
    bp = get_blueprint_by_id_from_db(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint non trovato nel catalogo")
    return bp
