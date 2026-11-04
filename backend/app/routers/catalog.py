from fastapi import APIRouter, HTTPException
from typing import List
from ..models import Blueprint
from ..services.storage import get_all_blueprints_from_db, get_blueprint_by_id_from_db

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


@router.get("/blueprints", response_model=List[Blueprint], summary="Ottieni l'elenco dei blueprint dinamici dal database")
def list_blueprints():
    """Ritorna tutti i blueprint attivi memorizzati nel database relazionale PostgreSQL."""
    return get_all_blueprints_from_db()


@router.get("/blueprints/{blueprint_id}", response_model=Blueprint, summary="Dettaglio e schema parametri di un blueprint")
def get_blueprint(blueprint_id: str):
    """Ritorna lo schema dei parametri da richiedere all'utente per lo specifico blueprint."""
    bp = get_blueprint_by_id_from_db(blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint non trovato nel catalogo")
    return bp
