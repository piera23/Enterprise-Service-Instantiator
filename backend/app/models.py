# ==============================================================================
# MODELS.PY - Schemi Dati Pydantic per Validazione e Serializzazione API
# Definisce le entità del catalogo, richieste di provisioning, istanze e statistiche FinOps
# ==============================================================================

# Classi base per la dichiarazione dei modelli e dei vincoli di validazione Pydantic
from pydantic import BaseModel, Field
# Tipizzazione Python per collezioni, valori opzionali e strutture eterogenee
from typing import List, Dict, Any, Optional
# Timestamp per date e ore
from datetime import datetime
# Enumerazioni per valori ammessi a livello di tipo
from enum import Enum


class EnvironmentEnum(str, Enum):
    """Enumerazione degli ambienti di deployment consentiti con policy differenziate."""
    DEV = "dev"           # Ambiente di sviluppo e collaudo individuale
    STAGING = "staging"   # Ambiente di pre-produzione per test di integrazione
    PROD = "prod"         # Ambiente di produzione con requisiti di approvazione obbligatori


class InstanceStatus(str, Enum):
    """Stati del ciclo di vita di un'istanza all'interno della piattaforma."""
    PENDING = "PENDING"                         # In attesa di elaborazione nella coda
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"     # Bloccata in attesa di approvazione manuale (budget o prod)
    PROVISIONING = "PROVISIONING"               # Provisioning e configurazione in corso
    ACTIVE = "ACTIVE"                           # Risorsa creata, operativa e verificata con successo
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"   # Operazione Day-2 in esecuzione (es. riavvio o estensione)
    STOPPED = "STOPPED"                         # Servizio temporaneamente arrestato per risparmio costi
    FAILED = "FAILED"                           # Errore riscontrato durante il provisioning o l'avvio
    TERMINATED = "TERMINATED"                   # Risorsa completamente dismessa e rimossa


class BlueprintFieldOption(BaseModel):
    """Opzione selezionabile per un campo di input a scelta multipla (select/dropdown)."""
    label: str                     # Etichetta descrittiva mostrata nell'interfaccia utente
    value: str                     # Valore tecnico passato al connettore backend
    cost_multiplier: float = 1.0   # Moltiplicatore sul costo mensile di base del blueprint


class BlueprintField(BaseModel):
    """Definizione di un campo dinamico del form di provisioning per un blueprint."""
    name: str                                           # Nome della variabile (chiave nel dizionario parameters)
    label: str                                          # Etichetta visualizzata nel portale
    type: str                                           # Tipo di widget: "text", "select", "number", "boolean"
    description: str                                    # Spiegazione e guida per l'utente compilatore
    required: bool = True                               # Indica se il campo è obbligatorio
    default: Optional[Any] = None                       # Valore preselezionato di default
    options: Optional[List[BlueprintFieldOption]] = None # Lista di scelte se type == "select"


class Blueprint(BaseModel):
    """Modello del catalogo dei servizi: definisce un template di infrastruttura instanziabile."""
    id: str                                          # Identificativo univoco (es. "postgres-enterprise")
    title: str                                       # Titolo visualizzato nella card del catalogo
    category: str                                    # Categoria logica (es. "Database & Storage")
    badge: str                                       # Badge di risalto (es. "Golden Path", "DevOps Core")
    icon: str                                        # Nome icona Lucide (es. "database", "server", "globe")
    description: str                                 # Descrizione breve visualizzata nella card
    long_description: str                            # Descrizione estesa con dettagli architetturali
    connector_id: str                                # ID del connettore responsabile dell'istanziazione
    base_monthly_cost: float                         # Costo mensile minimo di partenza in Euro
    provisioning_time_seconds: int = 15              # Tempo medio stimato per completare il provisioning
    auto_approval_limit_eur: float = 250.0           # Soglia di costo FinOps per l'approvazione automatica
    fields: List[BlueprintField] = []                # Parametri configurabili dall'utente
    day2_actions: List[str] = ["restart", "extend_ttl"] # Azioni di gestione Day-2 supportate


class ProvisionRequest(BaseModel):
    """Payload inviato dal client per richiedere il provisioning di una nuova istanza."""
    blueprint_id: str                                # Identificativo del blueprint desiderato
    name: str = Field(..., min_length=3, max_length=60) # Nome identificativo dell'istanza
    owner_name: str                                  # Nome e cognome del richiedente
    owner_email: str                                 # Indirizzo email aziendale del richiedente
    team: str                                        # Team di appartenenza (es. "Platform & DevOps Core")
    cost_center: str                                 # Centro di costo aziendale per imputazione spesa (FinOps)
    environment: EnvironmentEnum = EnvironmentEnum.DEV # Ambiente di destinazione
    ttl_days: int = Field(default=14, ge=1, le=90)   # Time-To-Live in giorni (massimo 90 giorni)
    parameters: Dict[str, Any] = {}                  # Mappa dei parametri personalizzati compilati nel form


class ActionRequest(BaseModel):
    """Richiesta di esecuzione di un'azione Day-2 su un'istanza già esistente."""
    action: str                                      # Azione richiesta: "restart", "stop", "start", "extend_ttl", "backup"
    parameters: Optional[Dict[str, Any]] = None      # Eventuali parametri aggiuntivi (es. {"days": 7})


class Instance(BaseModel):
    """Rappresentazione completa di un'istanza creata all'interno della piattaforma."""
    id: str                                          # ID univoco generato dal sistema (es. "inst-a1b2c3d4")
    blueprint_id: str                                # Blueprint da cui deriva l'istanza
    blueprint_title: str                             # Nome leggibile del blueprint
    category: str                                    # Categoria architetturale
    icon: str                                        # Icona visiva dell'istanza
    name: str                                        # Nome assegnato dall'utente
    owner_name: str                                  # Nome dell'owner
    owner_email: str                                 # Email dell'owner
    team: str                                        # Team assegnatario
    cost_center: str                                 # Centro di costo
    environment: EnvironmentEnum                     # Ambiente (dev, staging, prod)
    status: InstanceStatus                           # Stato corrente del ciclo di vita
    progress_percentage: int = 0                     # Avanzamento percentuale del provisioning (0-100)
    progress_message: str = "In attesa di elaborazione" # Messaggio descrittivo dello stato corrente
    created_at: str                                  # Data e ora di creazione
    expires_at: str                                  # Data e ora di scadenza programmata (TTL)
    ttl_days: int                                    # Giorni totali di validità
    monthly_cost: float                              # Costo mensile calcolato per l'istanza
    endpoints: Dict[str, str] = {}                   # URL e indirizzi di rete per accedere al servizio
    credentials: Dict[str, str] = {}                 # Credenziali o riferimenti sicuri generati
    parameters: Dict[str, Any] = {}                  # Parametri utilizzati per l'istanziazione
    day2_actions: List[str] = []                     # Lista di azioni eseguibili sull'istanza
    logs: List[str] = []                             # Registro cronologico delle operazioni svolte


class ConnectorInfo(BaseModel):
    """Informazioni e metriche di stato su uno dei connettori di backend registrati."""
    id: str                                          # ID del connettore (es. "docker-connector")
    name: str                                        # Nome completo del connettore
    type: str                                        # Tipologia: "container", "process", "cloud", "database", "k8s", "saas"
    description: str                                 # Descrizione delle capacità del connettore
    status: str = "ONLINE"                           # Stato di salute della connessione
    active_instances_count: int = 0                  # Numero di istanze attualmente attive su questo connettore


class FinOpsStats(BaseModel):
    """Statistiche aggregate di FinOps, consumo di budget e risparmio generato."""
    total_active_instances: int                      # Numero totale di istanze in esecuzione
    total_monthly_spend: float                       # Spesa totale mensile allocata in Euro
    total_savings_via_ttl: float                     # Risparmio stimato ottenuto spegnendo le risorse tramite TTL
    instances_by_environment: Dict[str, int]         # Distribuzione delle istanze per ambiente (dev, staging, prod)
    instances_by_category: Dict[str, int]            # Distribuzione delle istanze per categoria
