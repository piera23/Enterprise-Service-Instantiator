# ==============================================================================
# ROUTERS/BACKOFFICE.PY - Router API Backoffice Enterprise & IAM
# Gestione Utenti, Assegnazione Team & Budget FinOps, Blueprint Studio e Audit Trail
# ==============================================================================

# Costruttori di rotte, dependency injection, gestione eccezioni e codici HTTP
from fastapi import APIRouter, Depends, HTTPException, status
# Sessione del database relazionale SQLAlchemy
from sqlalchemy.orm import Session
# Modelli Pydantic per la validazione delle richieste
from pydantic import BaseModel
# Tipizzazione Python
from typing import List, Optional, Dict, Any
# Serializzazione JSON
import json
# Generazione identificatori UUID
import uuid

# Dependency injection database
from ..database import get_db
# Modelli ORM del database
from ..db_models import User, Team, BlueprintModel, BlueprintInput, AuditLog, InstanceRecord
# Hashing password, utente corrente e guardrails di autorizzazione basati su ruoli (RBAC)
from ..auth import hash_password, get_current_user, require_roles
# Funzione per la registrazione di log di audit
from ..services.storage import log_audit

# Istanziazione del router con prefisso di percorso e tag OpenAPI
router = APIRouter(prefix="/api/v1/backoffice", tags=["Enterprise Backoffice & IAM"])

# ------------------------------------------------------------------------------
# SCHEMI PYDANTIC PER LE RICHIESTE DI BACKOFFICE
# ------------------------------------------------------------------------------

class UserCreateRequest(BaseModel):
    """Payload per la creazione di un nuovo utente con ruolo e team assegnati."""
    username: str
    email: str
    password: str
    role: str = "developer"  # admin, devops_lead, developer, auditor
    team_id: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Payload per l'aggiornamento del profilo utente, ruolo o reset 2FA."""
    role: Optional[str] = None
    team_id: Optional[str] = None
    is_active: Optional[bool] = None
    reset_2fa: Optional[bool] = False


class TeamCreateRequest(BaseModel):
    """Payload per la creazione di un nuovo team con centro di costo e budget mensile."""
    name: str
    slug: str
    cost_center: str
    lead_email: str
    monthly_budget_eur: float = 2000.0
    max_instances: int = 25


class BlueprintInputFieldDTO(BaseModel):
    """Definizione di un campo dinamico configurabile per un nuovo Blueprint."""
    name: str
    label: str
    input_type: str  # text, select, number, boolean, secret_vault
    description: Optional[str] = None
    required: bool = True
    default_value: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    display_order: int = 0


class BlueprintCreateRequest(BaseModel):
    """Payload per la pubblicazione di un nuovo template di infrastruttura dal Blueprint Studio."""
    id: str  # es. "k8s-helm-release"
    title: str
    category_name: str
    badge: str = "Custom DevOps"
    icon: str = "server"
    description: str
    long_description: Optional[str] = None
    connector_id: str  # docker-connector, process-connector, k8s-adapter, etc.
    base_monthly_cost: float = 30.0
    provisioning_time_seconds: int = 8
    auto_approval_limit_eur: float = 200.0
    inputs: List[BlueprintInputFieldDTO] = []


# ------------------------------------------------------------------------------
# 1. GESTIONE UTENTI (IAM & USER MANAGEMENT)
# ------------------------------------------------------------------------------

@router.get("/users", summary="Elenco utenti con ruoli e team")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead", "auditor"]))
):
    """
    Ritorna l'elenco completo degli utenti aziendali con team di appartenenza,
    stato di attivazione, configurazione 2FA e data di registrazione.
    Riservato ai ruoli: admin, devops_lead, auditor.
    """
    users = db.query(User).all()
    result = []
    for u in users:
        t_name = u.team.name if u.team else "Nessun Team"
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "team_id": u.team_id,
            "team_name": t_name,
            "is_active": u.is_active,
            "is_2fa_enabled": u.is_2fa_enabled,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None,
            "last_login": u.last_login.strftime("%Y-%m-%d %H:%M:%S") if u.last_login else "Mai"
        })
    return result


@router.post("/users", status_code=status.HTTP_201_CREATED, summary="Crea un nuovo utente aziendale")
def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead"]))
):
    """
    Crea un nuovo utente aziendale, ne calcola l'hash della password con PBKDF2
    e registra l'evento nel registro immutabile di audit.
    """
    existing = db.query(User).filter((User.email == req.email) | (User.username == req.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email o Username già esistenti.")

    new_user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role,
        team_id=req.team_id,
        is_active=True,
        is_2fa_enabled=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Scrittura nel registro di audit
    log_audit(current_user.email, "USER_CREATED", new_user.id, f"Creato utente {new_user.email} con ruolo {new_user.role}")
    return {"status": "SUCCESS", "message": f"Utente {new_user.username} creato con successo.", "user_id": new_user.id}


@router.put("/users/{user_id}", summary="Modifica ruolo, team o reset 2FA")
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead"]))
):
    """
    Consente agli amministratori di modificare il ruolo RBAC, associare l'utente a un altro team
    o resettare la chiave 2FA in caso di smarrimento del dispositivo mobile.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    if req.role is not None:
        user.role = req.role
    if req.team_id is not None:
        user.team_id = req.team_id
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.reset_2fa:
        user.is_2fa_enabled = False
        user.totp_secret = None

    db.commit()
    log_audit(current_user.email, "USER_UPDATED", user.id, f"Aggiornato utente {user.email}")
    return {"status": "SUCCESS", "message": "Utente aggiornato con successo."}


@router.delete("/users/{user_id}", summary="Elimina un utente")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """
    Elimina un account utente. Impedisce all'amministratore di eliminare il proprio account.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Non puoi eliminare il tuo stesso account.")

    email = user.email
    db.delete(user)
    db.commit()
    log_audit(current_user.email, "USER_DELETED", user_id, f"Eliminato utente {email}")
    return {"status": "SUCCESS", "message": f"Utente {email} eliminato."}


# ------------------------------------------------------------------------------
# 2. GESTIONE TEAM & SQUAD (MULTI-TENANCY & FINOPS BUDGET)
# ------------------------------------------------------------------------------

@router.get("/teams", summary="Elenco team con statistiche di budget e membri")
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead", "auditor"]))
):
    """
    Calcola per ciascun team il consumo di budget in tempo reale,
    la percentuale di utilizzo rispetto al budget massimo e il numero di membri.
    """
    teams = db.query(Team).all()
    result = []
    for t in teams:
        members_count = len(t.users)
        instances_count = db.query(InstanceRecord).filter(InstanceRecord.cost_center == t.cost_center).count()
        # Calcolo spesa corrente delle istanze attive assegnate al centro di costo del team
        team_instances = db.query(InstanceRecord).filter(InstanceRecord.cost_center == t.cost_center).all()
        current_spend = sum(i.monthly_cost for i in team_instances if i.status in ["ACTIVE", "PROVISIONING"])

        result.append({
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "cost_center": t.cost_center,
            "lead_email": t.lead_email,
            "monthly_budget_eur": t.monthly_budget_eur,
            "current_spend_eur": round(current_spend, 2),
            "budget_usage_pct": round((current_spend / t.monthly_budget_eur * 100) if t.monthly_budget_eur > 0 else 0, 1),
            "max_instances": t.max_instances,
            "members_count": members_count,
            "active_instances_count": instances_count
        })
    return result


@router.post("/teams", status_code=status.HTTP_201_CREATED, summary="Crea un nuovo team aziendale")
def create_team(
    req: TeamCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead"]))
):
    """Crea un nuovo reparto/squad con relativo centro di costo per le policy FinOps."""
    existing = db.query(Team).filter((Team.name == req.name) | (Team.slug == req.slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team con questo nome o slug già esistente.")

    new_team = Team(
        name=req.name,
        slug=req.slug,
        cost_center=req.cost_center,
        lead_email=req.lead_email,
        monthly_budget_eur=req.monthly_budget_eur,
        max_instances=req.max_instances
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    log_audit(current_user.email, "TEAM_CREATED", new_team.id, f"Creato team {new_team.name} con budget €{new_team.monthly_budget_eur}")
    return {"status": "SUCCESS", "message": f"Team {new_team.name} creato.", "team_id": new_team.id}


# ------------------------------------------------------------------------------
# 3. BLUEPRINT STUDIO (CREAZIONE TEMPLATE DINAMICI NO-CODE)
# ------------------------------------------------------------------------------

@router.get("/blueprints", summary="Elenco completo dei Blueprint dal database")
def list_backoffice_blueprints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead"]))
):
    """Restituisce tutti i blueprint con i dettagli completi dei campi di input per l'editor."""
    models = db.query(BlueprintModel).all()
    result = []
    for m in models:
        inputs_dto = []
        for inp in m.inputs:
            inputs_dto.append({
                "id": inp.id,
                "name": inp.name,
                "label": inp.label,
                "input_type": inp.input_type,
                "description": inp.description,
                "required": inp.required,
                "default_value": inp.default_value,
                "options": inp.options,
                "display_order": inp.display_order
            })
        result.append({
            "id": m.id,
            "title": m.title,
            "category_name": m.category_name,
            "badge": m.badge,
            "icon": m.icon,
            "description": m.description,
            "long_description": m.long_description,
            "connector_id": m.connector_id,
            "base_monthly_cost": m.base_monthly_cost,
            "provisioning_time_seconds": m.provisioning_time_seconds,
            "auto_approval_limit_eur": m.auto_approval_limit_eur,
            "is_published": m.is_published,
            "inputs_count": len(m.inputs),
            "inputs": inputs_dto
        })
    return result


@router.post("/blueprints", status_code=status.HTTP_201_CREATED, summary="Crea un nuovo Blueprint con campi dinamici dal Backoffice")
def create_blueprint(
    req: BlueprintCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead"]))
):
    """
    Crea e pubblica un nuovo template di infrastruttura con form dinamico personalizzato.
    I nuovi blueprint compaiono immediatamente nel catalogo degli sviluppatori senza riavviare il backend.
    """
    existing = db.query(BlueprintModel).filter(BlueprintModel.id == req.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Un blueprint con ID '{req.id}' esiste già.")

    bp = BlueprintModel(
        id=req.id,
        title=req.title,
        category_name=req.category_name,
        badge=req.badge,
        icon=req.icon,
        description=req.description,
        long_description=req.long_description,
        connector_id=req.connector_id,
        base_monthly_cost=req.base_monthly_cost,
        provisioning_time_seconds=req.provisioning_time_seconds,
        auto_approval_limit_eur=req.auto_approval_limit_eur,
        is_published=True
    )
    db.add(bp)
    db.commit()

    # Inserimento dei campi di input dinamici
    order = 1
    for inp in req.inputs:
        new_inp = BlueprintInput(
            blueprint_id=bp.id,
            name=inp.name,
            label=inp.label,
            input_type=inp.input_type,
            description=inp.description,
            required=inp.required,
            default_value=inp.default_value,
            options_json=json.dumps(inp.options) if inp.options else "[]",
            display_order=inp.display_order or order
        )
        db.add(new_inp)
        order += 1

    db.commit()
    log_audit(current_user.email, "BLUEPRINT_CREATED", bp.id, f"Pubblicato nuovo template '{bp.title}'")
    return {"status": "SUCCESS", "message": f"Blueprint '{bp.title}' salvato e pubblicato nel catalogo aziendale!", "id": bp.id}


@router.delete("/blueprints/{bp_id}", summary="Elimina o ritira un blueprint dal catalogo")
def delete_blueprint(
    bp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """Elimina un blueprint e i suoi campi di input associati dal catalogo."""
    bp = db.query(BlueprintModel).filter(BlueprintModel.id == bp_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint non trovato.")

    title = bp.title
    db.delete(bp)
    db.commit()
    log_audit(current_user.email, "BLUEPRINT_DELETED", bp_id, f"Eliminato blueprint '{title}'")
    return {"status": "SUCCESS", "message": f"Blueprint '{title}' eliminato con successo."}


# ------------------------------------------------------------------------------
# 4. AUDIT TRAIL LOGS (CONFORMITÀ E TRACCIABILITÀ COMPLIANCE)
# ------------------------------------------------------------------------------

@router.get("/audit-logs", summary="Registro immutabile degli eventi di audit")
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "devops_lead", "auditor"]))
):
    """
    Restituisce gli ultimi 150 log di audit immutabili per controlli di conformità e sicurezza.
    """
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(150).all()
    return [{
        "id": l.id,
        "user_email": l.user_email,
        "action": l.action,
        "resource_id": l.resource_id,
        "details": l.details,
        "ip_address": l.ip_address,
        "timestamp": l.timestamp
    } for l in logs]
