# Enterprise Service Instantiator (ESI)
> Portale Self-Service aziendale per l'istanziazione controllata di ambienti Cloud, database, microservizi e piattaforme SaaS esterne.

---

## 🎯 Panoramica del Progetto

Il progetto implementa una piattaforma di **Platform Engineering** ("Internal Developer Platform"):
- **Per gli utenti (anche non tecnici):** Un catalogo a schede stile "App Store" con un questionario guidato in 3 passaggi, notifiche di avanzamento in tempo reale, consegna delle credenziali "chiavi in mano" e controlli Day-2 (riavvio, prolungamento scadenza, de-provisioning).
- **Per l'azienda (IT & DevOps):** Un'architettura modulare **API-First** basata sul **Connector/Adapter Pattern**, che consente di interfacciarsi con qualsiasi tecnologia interna o fornitore SaaS esterno tramite un contratto unificato. Include controlli di governance automatica (Guardrails), policy di budget FinOps e Time-To-Live (TTL) anti-spreco.

---

## 🚀 Avvio Rapido

Il backend FastAPI include già il web server statico integrato: con **un solo comando** viene avviato sia il backend API sia l'interfaccia utente web.

### 1. Prerequisiti
- Python 3.10+ (o l'ambiente virtuale già configurato in `.venv`)

### 2. Avvio del Server
```powershell
# Dalla cartella principale del progetto:
.\.venv\Scripts\python.exe backend\run.py
```

### 3. Accesso
- 🌐 **Portale Web Utente:** [http://localhost:8080](http://localhost:8080)
- 📚 **Documentazione API Interattiva (Swagger UI):** [http://localhost:8080/docs](http://localhost:8080/docs)
- 📖 **Documentazione ReDoc:** [http://localhost:8080/redoc](http://localhost:8080/redoc)

---

## 🏛️ Architettura del Codice

```
istanziatore/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entrypoint FastAPI, CORS e mount del portale web
│   │   ├── config.py            # Configurazioni e percorsi cartelle
│   │   ├── models.py            # Modelli dati Pydantic (Blueprint, Instance, Actions, FinOps)
│   │   ├── catalog/
│   │   │   └── blueprints.py    # Definizione dichiarativa dei servizi a catalogo (Golden Paths)
│   │   ├── connectors/          # ADAPTER PATTERN: i connettori verso piattaforme terze
│   │   │   ├── base.py          # Interfaccia comune (SPI)
│   │   │   ├── cloud_adapter.py # Connettore per VM / Cloud Infrastructure
│   │   │   ├── database_adapter.py # Connettore per Database PostgreSQL & Vault
│   │   │   ├── k8s_adapter.py   # Connettore per Kubernetes & GitLab CI/CD
│   │   │   └── saas_adapter.py  # Connettore per API SaaS esterne
│   │   ├── services/
│   │   │   ├── orchestrator.py  # Gestione asincrona del ciclo di vita e dei job
│   │   │   ├── policy_engine.py # Regole di auto-approvazione, budget cap e guardrails
│   │   │   └── storage.py       # Persistenza JSON/Database dello stato
│   │   └── routers/             # Endpoint RESTful
│   │       ├── catalog.py       # GET /api/v1/catalog/blueprints
│   │       ├── instances.py     # POST /api/v1/instances, Day-2 actions, Delete
│   │       ├── connectors.py    # GET /api/v1/connectors
│   │       └── stats.py         # GET /api/v1/stats (FinOps & Analytics)
│   ├── requirements.txt
│   └── run.py                   # Script di avvio rapido con Uvicorn
└── frontend/
    └── index.html               # SPA moderna in React, Tailwind CSS e Lucide Icons
```

---

## 🔌 Come Aggiungere una Nuova Piattaforma (Nuovo Connettore)

Per collegare una nuova piattaforma (es. *Salesforce*, *VMware vSphere*, *AWS S3* o un software interno):

1. **Crea un nuovo adapter in `backend/app/connectors/mio_adapter.py`**:
   ```python
   from .base import BaseConnector

   class MioAdapter(BaseConnector):
       id = "mio-adapter"
       name = "Mio Connettore Piattaforma"
       platform_type = "custom"
       description = "Descrizione della piattaforma"

       def validate_parameters(self, parameters):
           return True, "Parametri validi"

       def calculate_cost(self, base_cost, parameters):
           return base_cost

       async def apply_provisioning(self, instance_id, name, parameters, progress_callback=None):
           # Chiama le API esterne o esegue script di provisioning
           await progress_callback(50, "Creazione in corso...")
           return {
               "endpoints": {"Link": "https://mia-piattaforma.internal"},
               "credentials": {"Token": "token-segreto"}
           }

       async def execute_action(self, instance_id, action, parameters=None):
           return {"status": "SUCCESS"}

       async def destroy(self, instance_id):
           return True
   ```
2. **Registralo nel registro in `backend/app/connectors/__init__.py`**.
3. **Crea la scheda visiva nel catalogo in `backend/app/catalog/blueprints.py`**.

L'interfaccia grafica e le API lo renderanno immediatamente disponibile a tutti gli utenti dell'azienda!
