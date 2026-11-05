# ==============================================================================
# BLUEPRINTS.PY - Definizione Statica Template e Blueprint del Catalogo
# Contiene i modelli e le opzioni dei servizi provisionabili per fallback e test
# ==============================================================================

# Tipizzazione Python per liste e opzionali
from typing import List, Optional
# Schemi Pydantic per blueprint e campi dinamici
from ..models import Blueprint, BlueprintField, BlueprintFieldOption

# Elenco completo dei Blueprint enterprise preconfigurati nel catalogo
BLUEPRINTS: List[Blueprint] = [
    # --------------------------------------------------------------------------
    # 1. DATABASE & STORAGE
    # --------------------------------------------------------------------------
    Blueprint(
        id="postgres-enterprise",
        title="PostgreSQL 16 Enterprise Cluster",
        category="Database & Storage",
        badge="DevOps Core",
        icon="database",
        description="Cluster PostgreSQL 16 ad alte prestazioni con backup orari, replica e credenziali Vault.",
        long_description=(
            "Istanzia un database PostgreSQL 16 con parametri di conformità enterprise, crittografia dei dischi "
            "e gestione automatica delle credenziali salvate su HashiCorp Vault. Include healthcheck TCP/SQL in tempo reale."
        ),
        connector_id="docker-connector",
        base_monthly_cost=45.0,
        provisioning_time_seconds=6,
        auto_approval_limit_eur=200.0,
        fields=[
            BlueprintField(
                name="db_name",
                label="Nome Database",
                type="text",
                description="Identificativo univoco del database (es. payment_db)",
                required=True,
                default="enterprise_db"
            ),
            BlueprintField(
                name="db_size",
                label="Dimensionamento & Risorse",
                type="select",
                description="Profilo CPU/RAM e capacità storage",
                required=True,
                default="small",
                options=[
                    BlueprintFieldOption(label="Small (2 vCPU, 4GB RAM, 50GB SSD)", value="small", cost_multiplier=1.0),
                    BlueprintFieldOption(label="Medium (4 vCPU, 16GB RAM, 200GB SSD)", value="medium", cost_multiplier=2.0),
                    BlueprintFieldOption(label="High-Availability (8 vCPU, 32GB RAM, 500GB SSD)", value="large", cost_multiplier=3.5),
                ]
            ),
            BlueprintField(
                name="service_type",
                label="Engine",
                type="select",
                description="Versione database",
                required=True,
                default="postgres",
                options=[BlueprintFieldOption(label="PostgreSQL 16 Alpine", value="postgres", cost_multiplier=1.0)]
            )
        ],
        day2_actions=["restart", "stop", "start", "backup", "extend_ttl"]
    ),

    Blueprint(
        id="redis-cluster",
        title="Redis 7 In-Memory Cache & Message Broker",
        category="Database & Storage",
        badge="In-Memory",
        icon="sparkles",
        description="Nodo Redis 7 Alpine a bassa latenza per caching, session storage e code asincrone Pub/Sub.",
        long_description=(
            "Istanzia un nodo Redis 7 ottimizzato per alte prestazioni con persistenza AOF e porta TCP dinamica."
        ),
        connector_id="docker-connector",
        base_monthly_cost=18.0,
        provisioning_time_seconds=4,
        auto_approval_limit_eur=100.0,
        fields=[
            BlueprintField(
                name="service_type",
                label="Driver",
                type="select",
                description="Tipo container",
                required=True,
                default="redis",
                options=[BlueprintFieldOption(label="Redis 7 Alpine", value="redis", cost_multiplier=1.0)]
            )
        ],
        day2_actions=["restart", "stop", "start", "extend_ttl"]
    ),

    # --------------------------------------------------------------------------
    # 2. NETWORKING, INGRESS & WEB
    # --------------------------------------------------------------------------
    Blueprint(
        id="nginx-ingress-proxy",
        title="Nginx Reverse Proxy & Ingress Controller",
        category="Networking & Ingress",
        badge="Networking",
        icon="globe",
        description="Reverse proxy con terminazione SSL, bilanciamento di carico e routing verso i servizi interni.",
        long_description=(
            "Configura un gateway Nginx con regole di rate limiting, compressione gzip, header di sicurezza OWASP "
            "e routing automatico dei path verso i microservizi o container interni."
        ),
        connector_id="docker-connector",
        base_monthly_cost=20.0,
        provisioning_time_seconds=5,
        auto_approval_limit_eur=100.0,
        fields=[
            BlueprintField(
                name="customer_name",
                label="Nome Ingress / Dominio",
                type="text",
                description="Nome logico o dominio (es. api.corp.internal)",
                required=True,
                default="api-gateway"
            ),
            BlueprintField(
                name="service_type",
                label="Modalità Proxy",
                type="select",
                description="Profilo Nginx",
                required=True,
                default="web",
                options=[
                    BlueprintFieldOption(label="Standard Reverse Proxy & Ingress", value="web", cost_multiplier=1.0)
                ]
            )
        ],
        day2_actions=["restart", "stop", "start", "extend_ttl"]
    ),

    # --------------------------------------------------------------------------
    # 3. MICROSERVIZI CLOUD-NATIVE
    # --------------------------------------------------------------------------
    Blueprint(
        id="fastapi-microservice",
        title="Python Cloud-Native Microservice (FastAPI)",
        category="Microservizi & App",
        badge="Golden Path",
        icon="boxes",
        description="Microservizio asincrono pronto al deploy: Swagger UI, metriche Prometheus e Dockerfile.",
        long_description=(
            "Istanzia uno scaffolding pronto di un microservizio FastAPI con endpoint `/health`, `/metrics` per Prometheus, "
            "Pydantic V2, supporto database asincrono e test unitari PyTest già configurati."
        ),
        connector_id="process-connector",
        base_monthly_cost=25.0,
        provisioning_time_seconds=4,
        auto_approval_limit_eur=150.0,
        fields=[
            BlueprintField(
                name="customer_name",
                label="Nome del Microservizio",
                type="text",
                description="Es. billing-service o user-mgmt-api",
                required=True,
                default="billing-service"
            )
        ],
        day2_actions=["restart", "stop", "extend_ttl"]
    ),

    # --------------------------------------------------------------------------
    # 4. CI/CD & GITOPS
    # --------------------------------------------------------------------------
    Blueprint(
        id="cicd-pipeline-scaffold",
        title="Pipeline CI/CD con SonarQube & Trivy Security",
        category="CI/CD & DevSecOps",
        badge="Security First",
        icon="shield-check",
        description="Generazione automatica di pipeline CI/CD con scansione vulnerabilità e test di qualità.",
        long_description=(
            "Configura repository Git (GitLab CI o GitHub Actions) con step automatizzati di linting, unit test, "
            "quality gate SonarQube, security scan Trivy per immagini container e deploy automatizzato."
        ),
        connector_id="k8s-adapter",
        base_monthly_cost=15.0,
        provisioning_time_seconds=5,
        auto_approval_limit_eur=100.0,
        fields=[
            BlueprintField(
                name="service_language",
                label="Stack Tecnologico",
                type="select",
                description="Linguaggio della pipeline",
                required=True,
                default="python-fastapi",
                options=[
                    BlueprintFieldOption(label="Python (FastAPI + Trivy Scanner)", value="python-fastapi", cost_multiplier=1.0),
                    BlueprintFieldOption(label="Node.js (TypeScript + ESLint)", value="nodejs-typescript", cost_multiplier=1.0),
                    BlueprintFieldOption(label="Java (Spring Boot + Maven)", value="java-springboot", cost_multiplier=1.2),
                    BlueprintFieldOption(label="Go (Golang + Govulncheck)", value="go-service", cost_multiplier=1.0)
                ]
            )
        ],
        day2_actions=["extend_ttl"]
    ),

    # --------------------------------------------------------------------------
    # 5. OBSERVABILITY & MONITORAGGIO
    # --------------------------------------------------------------------------
    Blueprint(
        id="observability-stack",
        title="Stack Monitoraggio & Metriche (Prometheus)",
        category="Observability & Logs",
        badge="Monitoring",
        icon="activity",
        description="Agente di monitoraggio centralizzato con metriche host, scraping container e alert.",
        long_description=(
            "Attiva il monitoraggio per metriche di sistema, CPU, memoria e latenza HTTP con endpoint compatibile Prometheus."
        ),
        connector_id="process-connector",
        base_monthly_cost=20.0,
        provisioning_time_seconds=4,
        auto_approval_limit_eur=100.0,
        fields=[
            BlueprintField(
                name="customer_name",
                label="Cluster / Target Monitorato",
                type="text",
                description="Es. cluster-staging o prod-infra",
                required=True,
                default="cluster-staging"
            )
        ],
        day2_actions=["restart", "stop", "extend_ttl"]
    ),

    # --------------------------------------------------------------------------
    # 6. KUBERNETES TENANT MULTI-SQUAD
    # --------------------------------------------------------------------------
    Blueprint(
        id="k8s-namespace-tenant",
        title="Kubernetes Namespace Isolato (Multi-Tenant)",
        category="Kubernetes & Cloud",
        badge="K8s Enterprise",
        icon="cpu",
        description="Namespace Kubernetes isolato con ResourceQuotas (CPU/RAM limit), NetworkPolicy e RBAC.",
        long_description=(
            "Crea un namespace Kubernetes isolato secondo i principi di zero-trust: quote compute massime prefissate, "
            "regole di traffico NetworkPolicy e ServiceAccount con permessi minimi."
        ),
        connector_id="k8s-adapter",
        base_monthly_cost=35.0,
        provisioning_time_seconds=6,
        auto_approval_limit_eur=250.0,
        fields=[
            BlueprintField(
                name="replicas",
                label="Dimensione Tenant",
                type="select",
                description="Quote massime pod e nodi",
                required=True,
                default="1",
                options=[
                    BlueprintFieldOption(label="Quota Base (Max 10 Pod, 8 CPU, 16GB RAM)", value="1", cost_multiplier=1.0),
                    BlueprintFieldOption(label="Quota Estesa (Max 50 Pod, 32 CPU, 64GB RAM)", value="2", cost_multiplier=2.5),
                ]
            )
        ],
        day2_actions=["restart", "extend_ttl"]
    )
]


def get_blueprint_by_id(blueprint_id: str) -> Optional[Blueprint]:
    """Cerca e restituisce il blueprint corrispondente dall'elenco statico di default."""
    for bp in BLUEPRINTS:
        if bp.id == blueprint_id:
            return bp
    return None
