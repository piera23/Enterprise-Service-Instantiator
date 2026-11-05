# ==============================================================================
# DB_MODELS.PY - Modelli Relazionali SQLAlchemy (PostgreSQL / SQLite)
# Gestisce multi-tenancy, utenti RBAC, 2FA, blueprint dinamici, istanze e audit log
# ==============================================================================

# Modulo standard per generare identificatori univoci UUIDv4
import uuid
# Modulo standard per la serializzazione e deserializzazione di campi JSON
import json
# Gestione dei timestamp data e ora in formato UTC
from datetime import datetime
# Tipi di colonna e vincoli di chiave per la definizione delle tabelle del database
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
# Gestione delle relazioni ORM tra tabelle (1-a-N, N-a-1)
from sqlalchemy.orm import relationship
# Classe base dichiarativa definita in database.py
from .database import Base


# ------------------------------------------------------------------------------
# 1. ORGANIZZAZIONI AZIENDALI (MULTI-TENANCY ROOT)
# ------------------------------------------------------------------------------
class Organization(Base):
    """Rappresenta l'entità aziendale o tenant di livello più alto."""
    __tablename__ = "organizations"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Ragione sociale o nome dell'organizzazione
    name = Column(String(100), nullable=False)
    # Slug univoco per URL e percorsi
    slug = Column(String(50), unique=True, nullable=False)
    # Identificativo del conto di fatturazione centrale (FinOps)
    billing_account = Column(String(50), default="CORP-BILLING-MAIN")
    # Data e ora di registrazione dell'organizzazione
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazione uno-a-molti con i Team aziendali, con cancellazione a cascata
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")


# ------------------------------------------------------------------------------
# 2. TEAM & SQUAD CON LIMITI FINOPS E CENTRI DI COSTO
# ------------------------------------------------------------------------------
class Team(Base):
    """Rappresenta una squad o reparto aziendale con un centro di costo e budget FinOps dedicato."""
    __tablename__ = "teams"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Chiave esterna verso l'organizzazione di appartenenza
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    # Nome del team (es. "Platform & DevOps Core")
    name = Column(String(100), unique=True, nullable=False)
    # Slug univoco
    slug = Column(String(50), unique=True, nullable=False)
    # Codice centro di costo (es. "CC-DEVOPS-01") per tracciamento spesa
    cost_center = Column(String(50), nullable=False)
    # Email del responsabile o Tech Lead del team
    lead_email = Column(String(100), nullable=False)
    # Budget mensile massimo allocato in Euro (limite FinOps)
    monthly_budget_eur = Column(Float, default=1500.0)
    # Numero massimo di istanze attive contemporaneamente
    max_instances = Column(Integer, default=20)
    # Data di creazione del team
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazione inversa con l'organizzazione
    organization = relationship("Organization", back_populates="teams")
    # Relazione con gli utenti appartenenti al team
    users = relationship("User", back_populates="team")


# ------------------------------------------------------------------------------
# 3. UTENTI, RUOLI RBAC E SICUREZZA 2FA TOTP
# ------------------------------------------------------------------------------
class User(Base):
    """Modello per gli utenti aziendali con credenziali hash e configurazione 2FA."""
    __tablename__ = "users"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Chiave esterna facoltativa verso il team di appartenenza
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    # Username univoco per il login
    username = Column(String(50), unique=True, index=True, nullable=False)
    # Indirizzo email aziendale univoco
    email = Column(String(100), unique=True, index=True, nullable=False)
    # Password con hashing sicuro PBKDF2-HMAC-SHA256 e salt
    hashed_password = Column(String(255), nullable=False)
    # Ruolo RBAC: admin, devops_lead, developer, auditor
    role = Column(String(20), default="developer", nullable=False)
    # Flag account attivo / disattivato
    is_active = Column(Boolean, default=True)
    # Flag di abilitazione autenticazione a due fattori (2FA TOTP)
    is_2fa_enabled = Column(Boolean, default=False)
    # Chiave segreta TOTP in Base32 (utilizzata da Google Authenticator)
    totp_secret = Column(String(64), nullable=True)
    # Data di registrazione
    created_at = Column(DateTime, default=datetime.utcnow)
    # Timestamp dell'ultimo accesso effettuato
    last_login = Column(DateTime, nullable=True)

    # Relazione con il team
    team = relationship("Team", back_populates="users")


# ------------------------------------------------------------------------------
# 4. CATEGORIE DEI BLUEPRINT
# ------------------------------------------------------------------------------
class BlueprintCategory(Base):
    """Categorie organizzative del catalogo (es. Database, Microservizi, Networking)."""
    __tablename__ = "blueprint_categories"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Nome univoco della categoria
    name = Column(String(64), unique=True, nullable=False)
    # Descrizione della categoria
    description = Column(String(255), nullable=True)
    # Ordine di visualizzazione nella UI
    display_order = Column(Integer, default=0)

    # Relazione con i blueprint appartenenti a questa categoria
    blueprints = relationship("BlueprintModel", back_populates="category")


# ------------------------------------------------------------------------------
# 5. BLUEPRINT DINAMICI SALVATI NEL DATABASE (BLUEPRINT STUDIO)
# ------------------------------------------------------------------------------
class BlueprintModel(Base):
    """Modello persistente dei blueprint gestibile dinamicamente dal Backoffice senza modifiche al codice."""
    __tablename__ = "blueprints"

    # Identificativo testuale univoco (es. "postgres-enterprise")
    id = Column(String(64), primary_key=True)
    # Chiave esterna verso la categoria
    category_id = Column(String(36), ForeignKey("blueprint_categories.id"), nullable=True)
    # Nome leggibile della categoria di appartenenza
    category_name = Column(String(64), nullable=False, default="Database & Storage")
    # Titolo esteso del blueprint visualizzato nel catalogo
    title = Column(String(128), nullable=False)
    # Badge informativo (es. "DevOps Core", "Golden Path")
    badge = Column(String(32), default="DevOps Core")
    # Nome dell'icona Lucide (es. "database", "server")
    icon = Column(String(32), default="server")
    # Descrizione breve
    description = Column(String(255), nullable=False)
    # Descrizione tecnica estesa in formato testo
    long_description = Column(Text, nullable=True)
    # ID del connettore di esecuzione (es. "docker-connector", "process-connector")
    connector_id = Column(String(64), nullable=False)
    # Costo mensile di base in Euro
    base_monthly_cost = Column(Float, default=25.0)
    # Tempo stimato di provisioning in secondi
    provisioning_time_seconds = Column(Integer, default=10)
    # Soglia di costo FinOps per l'auto-approvazione
    auto_approval_limit_eur = Column(Float, default=200.0)
    # Flag di pubblicazione: solo i blueprint pubblicati appaiono nel catalogo agli utenti
    is_published = Column(Boolean, default=True)
    # Data di creazione del blueprint
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relazione con la categoria
    category = relationship("BlueprintCategory", back_populates="blueprints")
    # Relazione con i campi dinamici di input ordinati per display_order
    inputs = relationship("BlueprintInput", back_populates="blueprint", cascade="all, delete-orphan", order_by="BlueprintInput.display_order")


# ------------------------------------------------------------------------------
# 6. CAMPI DI INPUT DINAMICI DEL FORM DI UN BLUEPRINT
# ------------------------------------------------------------------------------
class BlueprintInput(Base):
    """Campi dinamici associati al template di provisioning di un Blueprint."""
    __tablename__ = "blueprint_inputs"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Chiave esterna verso il blueprint
    blueprint_id = Column(String(64), ForeignKey("blueprints.id"), nullable=False)
    # Nome tecnico del campo (es. "db_name", "db_size")
    name = Column(String(64), nullable=False)
    # Etichetta user-friendly visualizzata nel form
    label = Column(String(128), nullable=False)
    # Tipo di input: text, select, number, boolean, secret_vault
    input_type = Column(String(32), default="text")
    # Descrizione di aiuto per l'utente
    description = Column(String(255), nullable=True)
    # Flag obbligatorietà
    required = Column(Boolean, default=True)
    # Valore di default
    default_value = Column(String(255), nullable=True)
    # Opzioni per campi di tipo 'select' serializzate in JSON (etichetta, valore, moltiplicatore costo)
    options_json = Column(Text, default="[]")
    # Ordine di posizionamento all'interno del form
    display_order = Column(Integer, default=0)

    # Relazione inversa con il blueprint
    blueprint = relationship("BlueprintModel", back_populates="inputs")

    # Property per deserializzare automaticamente il campo JSON in una lista Python
    @property
    def options(self):
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    # Setter per serializzare la lista Python in formato JSON testuale
    @options.setter
    def options(self, val):
        self.options_json = json.dumps(val)


# ------------------------------------------------------------------------------
# 7. REGISTRO DELLE ISTANZE PROVISIONATE (ISTANZIATORE CORE)
# ------------------------------------------------------------------------------
class InstanceRecord(Base):
    """Tabella per memorizzare lo stato, le credenziali e gli endpoint di tutte le istanze create."""
    __tablename__ = "instances"

    # Identificativo univoco dell'istanza (es. "inst-a1b2c3d4")
    id = Column(String(64), primary_key=True, index=True)
    # Team e utente proprietari dell'istanza
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    # Riferimenti al blueprint originale
    blueprint_id = Column(String(64), nullable=False)
    blueprint_title = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    icon = Column(String(32), default="server")
    # Nome assegnato dall'utente
    name = Column(String(128), nullable=False)
    owner_name = Column(String(100), nullable=False)
    owner_email = Column(String(100), nullable=False)
    team = Column(String(100), nullable=False)
    cost_center = Column(String(50), nullable=False)
    # Ambiente (dev, staging, prod)
    environment = Column(String(20), default="dev")
    # Stato del ciclo di vita (PENDING, PROVISIONING, ACTIVE, STOPPED, FAILED, ecc.)
    status = Column(String(30), default="PENDING")
    # Percentuale di progresso (0-100)
    progress_percentage = Column(Integer, default=0)
    # Messaggio di stato corrente
    progress_message = Column(String(255), default="Inizializzazione...")
    # Timestamp di creazione e scadenza (TTL)
    created_at = Column(String(30), nullable=False)
    expires_at = Column(String(30), nullable=False)
    ttl_days = Column(Integer, default=14)
    # Costo mensile allocato
    monthly_cost = Column(Float, default=0.0)

    # Campi strutturati memorizzati come testo JSON per flessibilità multi-connettore
    endpoints_json = Column(Text, default="{}")
    credentials_json = Column(Text, default="{}")
    parameters_json = Column(Text, default="{}")
    env_vars_json = Column(Text, default="{}")
    tags_json = Column(Text, default="{}")
    day2_actions_json = Column(Text, default="[]")
    logs_json = Column(Text, default="[]")

    # Helper property/setter per la conversione trasparente JSON <-> Oggetti Python
    @property
    def endpoints(self):
        try:
            return json.loads(self.endpoints_json)
        except Exception:
            return {}

    @endpoints.setter
    def endpoints(self, val):
        self.endpoints_json = json.dumps(val)

    @property
    def credentials(self):
        try:
            return json.loads(self.credentials_json)
        except Exception:
            return {}

    @credentials.setter
    def credentials(self, val):
        self.credentials_json = json.dumps(val)

    @property
    def parameters(self):
        try:
            return json.loads(self.parameters_json)
        except Exception:
            return {}

    @parameters.setter
    def parameters(self, val):
        self.parameters_json = json.dumps(val)

    @property
    def env_vars(self):
        try:
            return json.loads(self.env_vars_json)
        except Exception:
            return {}

    @env_vars.setter
    def env_vars(self, val):
        self.env_vars_json = json.dumps(val)

    @property
    def tags(self):
        try:
            return json.loads(self.tags_json)
        except Exception:
            return {}

    @tags.setter
    def tags(self, val):
        self.tags_json = json.dumps(val)

    @property
    def day2_actions(self):
        try:
            return json.loads(self.day2_actions_json)
        except Exception:
            return []

    @day2_actions.setter
    def day2_actions(self, val):
        self.day2_actions_json = json.dumps(val)

    @property
    def logs(self):
        try:
            return json.loads(self.logs_json)
        except Exception:
            return []

    @logs.setter
    def logs(self, val):
        self.logs_json = json.dumps(val)


# ------------------------------------------------------------------------------
# 8. RICHIESTE DI APPROVAZIONE (GOVERNANCE & FINOPS APPROVAL WORKFLOW)
# ------------------------------------------------------------------------------
class ApprovalRequest(Base):
    """Traccia le richieste bloccate che richiedono il via libera di SecOps o Team Lead."""
    __tablename__ = "approval_requests"

    # Chiave primaria UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Istanza per cui è richiesta l'approvazione
    instance_id = Column(String(64), ForeignKey("instances.id"), nullable=False)
    # Utente che ha sottomesso la richiesta
    requested_by = Column(String(100), nullable=False)
    # Team richiedente
    team_name = Column(String(100), nullable=False)
    # Motivo del blocco: es. "PROD_ENVIRONMENT", "BUDGET_EXCEEDED", "HIGH_TTL"
    trigger_reason = Column(String(100), nullable=False)
    # Stato: PENDING, APPROVED, REJECTED
    status = Column(String(20), default="PENDING")
    # Eventuali note o motivazioni inserite dall'approvatore
    notes = Column(Text, nullable=True)
    # Timestamp della richiesta e della decisione
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(100), nullable=True)


# ------------------------------------------------------------------------------
# 9. AUDIT TRAIL LOGS (IMMUTABILE E CONFORME AGLI AUDIT DI SICUREZZA)
# ------------------------------------------------------------------------------
class AuditLog(Base):
    """Registro immutabile per tracciare tutte le azioni critiche svolte dagli utenti."""
    __tablename__ = "audit_logs"

    # ID incrementale
    id = Column(Integer, primary_key=True, index=True)
    # Email dell'utente che ha compiuto l'azione
    user_email = Column(String(100), nullable=False)
    # Codice dell'operazione (es. "USER_CREATED", "BLUEPRINT_CREATED", "INSTANCE_TERMINATED")
    action = Column(String(50), nullable=False)
    # ID della risorsa impattata (utente, istanza, blueprint)
    resource_id = Column(String(64), nullable=True)
    # Descrizione dettagliata dell'evento
    details = Column(Text, nullable=True)
    # Indirizzo IP del client
    ip_address = Column(String(45), default="127.0.0.1")
    # Data e ora dell'evento in formato stringa
    timestamp = Column(String(30), nullable=False)
