import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..database import SessionLocal, engine, Base
from ..db_models import (
    Organization,
    Team,
    User,
    BlueprintCategory,
    BlueprintModel,
    BlueprintInput,
    InstanceRecord,
    ApprovalRequest,
    AuditLog
)
from ..models import Instance, InstanceStatus, EnvironmentEnum, Blueprint, BlueprintField, BlueprintFieldOption
from ..auth import hash_password

# Crea tutte le tabelle nel database
Base.metadata.create_all(bind=engine)


def init_db_seeds():
    """Popola l'organizzazione, i team, gli utenti e i Blueprint con campi dinamici reali."""
    db = SessionLocal()
    try:
        # 1. Organizzazione
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Enterprise Digital Corp", slug="enterprise-digital-corp")
            db.add(org)
            db.commit()
            db.refresh(org)

        # 2. Team aziendali con budget FinOps
        teams_data = [
            ("Platform & DevOps Core", "platform-devops", "CC-DEVOPS-01", "devops@azienda.com", 5000.0, 50),
            ("E-Commerce Squad", "ecommerce-squad", "CC-ECOM-02", "ecom-lead@azienda.com", 2500.0, 25),
            ("FinTech & Payments", "fintech-payments", "CC-FIN-03", "fin-lead@azienda.com", 3500.0, 30),
            ("Data & AI Analytics", "data-analytics", "CC-DATA-04", "data-lead@azienda.com", 4000.0, 35)
        ]
        team_map = {}
        for name, slug, cc, lead, budget, max_inst in teams_data:
            t = db.query(Team).filter(Team.slug == slug).first()
            if not t:
                t = Team(
                    organization_id=org.id,
                    name=name,
                    slug=slug,
                    cost_center=cc,
                    lead_email=lead,
                    monthly_budget_eur=budget,
                    max_instances=max_inst
                )
                db.add(t)
                db.commit()
                db.refresh(t)
            team_map[slug] = t

        # 3. Utenti Enterprise
        users_seed = [
            ("admin_devops", "admin@azienda.com", "AdminPass123!", "admin", team_map.get("platform-devops").id),
            ("devops_lead", "devops.lead@azienda.com", "DevOpsPass123!", "devops_lead", team_map.get("platform-devops").id),
            ("mario_rossi", "mario.rossi@azienda.com", "DevPass123!", "developer", team_map.get("ecommerce-squad").id),
            ("laura_bianchi", "laura.bianchi@azienda.com", "DevPass123!", "developer", team_map.get("fintech-payments").id),
            ("auditor_compliance", "auditor@azienda.com", "AuditPass123!", "auditor", team_map.get("platform-devops").id)
        ]
        for username, email, pwd, role, tid in users_seed:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    username=username,
                    email=email,
                    hashed_password=hash_password(pwd),
                    role=role,
                    team_id=tid,
                    is_active=True,
                    is_2fa_enabled=False
                )
                db.add(u)
                db.commit()

        # 4. Blueprint Dinamici Reali (Non Cablati)
        blueprints_seed = [
            {
                "id": "postgres-enterprise",
                "title": "PostgreSQL 16 Enterprise Cluster",
                "category_name": "Database & Storage",
                "badge": "DevOps Core",
                "icon": "database",
                "description": "Cluster PostgreSQL 16 con replica sincrona, backup e crittografia AES-256.",
                "long_description": "Provisioning completo con binding di rete isolata, utenze Vault e policy di retention.",
                "connector_id": "docker-connector",
                "base_monthly_cost": 45.0,
                "provisioning_time_seconds": 6,
                "auto_approval_limit_eur": 250.0,
                "inputs": [
                    {
                        "name": "db_name",
                        "label": "Nome Database",
                        "input_type": "text",
                        "description": "Nome logico del database (es. payment_gateway_db)",
                        "required": True,
                        "default_value": "enterprise_db",
                        "display_order": 1
                    },
                    {
                        "name": "db_size",
                        "label": "Dimensionamento CPU / RAM",
                        "input_type": "select",
                        "description": "Profilo di calcolo per il cluster",
                        "required": True,
                        "default_value": "small",
                        "options_json": json.dumps([
                            {"label": "Small (2 vCPU, 4GB RAM, 50GB SSD)", "value": "small", "cost_multiplier": 1.0},
                            {"label": "Medium (4 vCPU, 16GB RAM, 200GB SSD)", "value": "medium", "cost_multiplier": 2.2},
                            {"label": "High-Availability (8 vCPU, 32GB RAM, 500GB SSD)", "value": "large", "cost_multiplier": 4.0}
                        ]),
                        "display_order": 2
                    },
                    {
                        "name": "vpc_network",
                        "label": "Rete / VPC di Assegnazione",
                        "input_type": "select",
                        "description": "Isolamento di rete secondo standard aziendali",
                        "required": True,
                        "default_value": "vpc-internal-secure",
                        "options_json": json.dumps([
                            {"label": "VPC Rete Interna Sicura (10.240.0.0/16)", "value": "vpc-internal-secure", "cost_multiplier": 1.0},
                            {"label": "VPC DMZ con Ingress Protetto (10.100.0.0/16)", "value": "vpc-dmz", "cost_multiplier": 1.1},
                            {"label": "VPC Isolamento PCI-DSS Compliance", "value": "vpc-pci-dss", "cost_multiplier": 1.3}
                        ]),
                        "display_order": 3
                    },
                    {
                        "name": "storage_profile",
                        "label": "Profilo Storage & IOPS",
                        "input_type": "select",
                        "description": "Tipo di storage sottostante",
                        "required": True,
                        "default_value": "gp3",
                        "options_json": json.dumps([
                            {"label": "General Purpose SSD (3000 IOPS)", "value": "gp3", "cost_multiplier": 1.0},
                            {"label": "Provisioned IOPS NVMe (10.000 IOPS)", "value": "io2", "cost_multiplier": 1.6}
                        ]),
                        "display_order": 4
                    },
                    {
                        "name": "backup_retention",
                        "label": "Policy di Backup & Snapshot",
                        "input_type": "select",
                        "description": "Frequenza e conservazione dei backup",
                        "required": True,
                        "default_value": "7",
                        "options_json": json.dumps([
                            {"label": "Giornaliero - Retention 7 Giorni", "value": "7", "cost_multiplier": 1.0},
                            {"label": "Orario - Retention 30 Giorni (Compliance)", "value": "30", "cost_multiplier": 1.25},
                            {"label": "Orario Multi-Region - Retention 90 Giorni", "value": "90", "cost_multiplier": 1.5}
                        ]),
                        "display_order": 5
                    },
                    {
                        "name": "data_sensitivity",
                        "label": "Classificazione Dati (Compliance)",
                        "input_type": "select",
                        "description": "Sensibilità dei dati secondo policy DPO",
                        "required": True,
                        "default_value": "internal",
                        "options_json": json.dumps([
                            {"label": "Uso Interno Aziendale", "value": "internal", "cost_multiplier": 1.0},
                            {"label": "Dati Sensibili / GDPR PII", "value": "gdpr_pii", "cost_multiplier": 1.1},
                            {"label": "Dati Finanziari Critici (PCI)", "value": "pci_critical", "cost_multiplier": 1.2}
                        ]),
                        "display_order": 6
                    }
                ]
            },
            {
                "id": "nginx-ingress-proxy",
                "title": "Nginx Ingress & Reverse Proxy Gateway",
                "category_name": "Networking & Ingress",
                "badge": "Networking",
                "icon": "globe",
                "description": "Gateway di ingresso con bilanciamento di carico, terminazione SSL e WAF.",
                "long_description": "Configura un reverse proxy con certificato TLS automatico e instradamento.",
                "connector_id": "docker-connector",
                "base_monthly_cost": 20.0,
                "provisioning_time_seconds": 5,
                "auto_approval_limit_eur": 120.0,
                "inputs": [
                    {
                        "name": "customer_name",
                        "label": "Nome Hostname / Dominio Desiderato",
                        "input_type": "text",
                        "description": "Es. checkout-api.internal.corp",
                        "required": True,
                        "default_value": "gateway.internal.corp",
                        "display_order": 1
                    },
                    {
                        "name": "ssl_mode",
                        "label": "Terminazione Certificato SSL/TLS",
                        "input_type": "select",
                        "description": "Modalità di cifratura TLS",
                        "required": True,
                        "default_value": "letsencrypt",
                        "options_json": json.dumps([
                            {"label": "Certificato Let's Encrypt Automatico", "value": "letsencrypt", "cost_multiplier": 1.0},
                            {"label": "Private Enterprise PKI Certificate", "value": "internal_ca", "cost_multiplier": 1.1}
                        ]),
                        "display_order": 2
                    },
                    {
                        "name": "rate_limiting",
                        "label": "Protezione Rate Limiting & WAF",
                        "input_type": "select",
                        "description": "Regole di contenimento attacchi DDoS/Bruteforce",
                        "required": True,
                        "default_value": "standard",
                        "options_json": json.dumps([
                            {"label": "Standard (100 req/sec per IP)", "value": "standard", "cost_multiplier": 1.0},
                            {"label": "Aggressive (20 req/sec con WAF Ruleset OWASP)", "value": "aggressive", "cost_multiplier": 1.2}
                        ]),
                        "display_order": 3
                    }
                ]
            },
            {
                "id": "fastapi-microservice",
                "title": "Microservizio Cloud-Native (Python FastAPI)",
                "category_name": "Microservizi & App",
                "badge": "Golden Path",
                "icon": "boxes",
                "description": "Scaffolding microservizio con metriche Prometheus, healthcheck e pipeline.",
                "long_description": "Genera l'ambiente con Swagger UI integrato e monitoraggio pronto per il deploy.",
                "connector_id": "process-connector",
                "base_monthly_cost": 25.0,
                "provisioning_time_seconds": 4,
                "auto_approval_limit_eur": 150.0,
                "inputs": [
                    {
                        "name": "customer_name",
                        "label": "Nome del Microservizio",
                        "input_type": "text",
                        "description": "Identificativo del servizio (es. order-fulfillment-api)",
                        "required": True,
                        "default_value": "order-service",
                        "display_order": 1
                    },
                    {
                        "name": "replicas",
                        "label": "Numero Minimo di Repliche",
                        "input_type": "select",
                        "description": "Scalabilità orizzontale dei container",
                        "required": True,
                        "default_value": "1",
                        "options_json": json.dumps([
                            {"label": "1 Istanza (Non ridondata per Dev/Test)", "value": "1", "cost_multiplier": 1.0},
                            {"label": "2 Istanze con Autoscaling (Staging/Prod)", "value": "2", "cost_multiplier": 1.8}
                        ]),
                        "display_order": 2
                    }
                ]
            },
            {
                "id": "redis-cluster",
                "title": "Redis 7 In-Memory Cache & Message Broker",
                "category_name": "Database & Storage",
                "badge": "In-Memory",
                "icon": "sparkles",
                "description": "Nodo Redis 7 Alpine a bassissima latenza per sessioni e code asincrone.",
                "long_description": "Nodo in-memory con persistenza AOF e porta dinamica.",
                "connector_id": "docker-connector",
                "base_monthly_cost": 18.0,
                "provisioning_time_seconds": 4,
                "auto_approval_limit_eur": 100.0,
                "inputs": [
                    {
                        "name": "service_type",
                        "label": "Modalità di Persistenza",
                        "input_type": "select",
                        "description": "Scelta del motore di caching",
                        "required": True,
                        "default_value": "redis",
                        "options_json": json.dumps([
                            {"label": "Redis 7 con Persistenza Ibrida AOF/RDB", "value": "redis", "cost_multiplier": 1.0}
                        ]),
                        "display_order": 1
                    }
                ]
            }
        ]

        for bp_dict in blueprints_seed:
            bp = db.query(BlueprintModel).filter(BlueprintModel.id == bp_dict["id"]).first()
            if not bp:
                bp = BlueprintModel(
                    id=bp_dict["id"],
                    title=bp_dict["title"],
                    category_name=bp_dict["category_name"],
                    badge=bp_dict["badge"],
                    icon=bp_dict["icon"],
                    description=bp_dict["description"],
                    long_description=bp_dict["long_description"],
                    connector_id=bp_dict["connector_id"],
                    base_monthly_cost=bp_dict["base_monthly_cost"],
                    provisioning_time_seconds=bp_dict["provisioning_time_seconds"],
                    auto_approval_limit_eur=bp_dict["auto_approval_limit_eur"],
                    is_published=True
                )
                db.add(bp)
                db.commit()

                # Aggiunta campi di input
                for inp_dict in bp_dict["inputs"]:
                    inp = BlueprintInput(
                        blueprint_id=bp.id,
                        name=inp_dict["name"],
                        label=inp_dict["label"],
                        input_type=inp_dict["input_type"],
                        description=inp_dict.get("description"),
                        required=inp_dict.get("required", True),
                        default_value=inp_dict.get("default_value"),
                        options_json=inp_dict.get("options_json", "[]"),
                        display_order=inp_dict.get("display_order", 0)
                    )
                    db.add(inp)
                db.commit()

    finally:
        db.close()


init_db_seeds()


# -------------------------------------------------------------------------
# FUNZIONI DI ACCESSO AI DATI E MAPPATURA
# -------------------------------------------------------------------------

def get_all_blueprints_from_db() -> List[Blueprint]:
    db = SessionLocal()
    try:
        models = db.query(BlueprintModel).filter(BlueprintModel.is_published == True).all()
        result = []
        for m in models:
            fields = []
            for inp in m.inputs:
                opts = []
                for o in inp.options:
                    opts.append(BlueprintFieldOption(
                        label=o.get("label", ""),
                        value=o.get("value", ""),
                        cost_multiplier=float(o.get("cost_multiplier", 1.0))
                    ))
                fields.append(BlueprintField(
                    name=inp.name,
                    label=inp.label,
                    type=inp.input_type,
                    description=inp.description or "",
                    required=inp.required,
                    default=inp.default_value,
                    options=opts if opts else None
                ))
            result.append(Blueprint(
                id=m.id,
                title=m.title,
                category=m.category_name,
                badge=m.badge,
                icon=m.icon,
                description=m.description,
                long_description=m.long_description or "",
                connector_id=m.connector_id,
                base_monthly_cost=m.base_monthly_cost,
                provisioning_time_seconds=m.provisioning_time_seconds,
                auto_approval_limit_eur=m.auto_approval_limit_eur,
                fields=fields,
                day2_actions=["restart", "stop", "start", "extend_ttl"]
            ))
        return result
    finally:
        db.close()


def get_blueprint_by_id_from_db(bp_id: str) -> Optional[Blueprint]:
    bps = get_all_blueprints_from_db()
    for bp in bps:
        if bp.id == bp_id:
            return bp
    return None


def record_to_instance(rec: InstanceRecord) -> Instance:
    return Instance(
        id=rec.id,
        blueprint_id=rec.blueprint_id,
        blueprint_title=rec.blueprint_title,
        category=rec.category,
        icon=rec.icon,
        name=rec.name,
        owner_name=rec.owner_name,
        owner_email=rec.owner_email,
        team=rec.team,
        cost_center=rec.cost_center,
        environment=EnvironmentEnum(rec.environment) if rec.environment in [e.value for e in EnvironmentEnum] else EnvironmentEnum.DEV,
        status=InstanceStatus(rec.status) if rec.status in [s.value for s in InstanceStatus] else InstanceStatus.PENDING,
        progress_percentage=rec.progress_percentage,
        progress_message=rec.progress_message,
        created_at=rec.created_at,
        expires_at=rec.expires_at,
        ttl_days=rec.ttl_days,
        monthly_cost=rec.monthly_cost,
        endpoints=rec.endpoints,
        credentials=rec.credentials,
        parameters=rec.parameters,
        day2_actions=rec.day2_actions,
        logs=rec.logs
    )


def get_all_instances() -> List[Instance]:
    db = SessionLocal()
    try:
        records = db.query(InstanceRecord).order_by(InstanceRecord.created_at.desc()).all()
        return [record_to_instance(r) for r in records]
    finally:
        db.close()


def get_instance_by_id(instance_id: str) -> Optional[Instance]:
    db = SessionLocal()
    try:
        rec = db.query(InstanceRecord).filter(InstanceRecord.id == instance_id).first()
        return record_to_instance(rec) if rec else None
    finally:
        db.close()


def upsert_instance(instance: Instance):
    db = SessionLocal()
    try:
        rec = db.query(InstanceRecord).filter(InstanceRecord.id == instance.id).first()
        if not rec:
            rec = InstanceRecord(id=instance.id)
            db.add(rec)

        rec.blueprint_id = instance.blueprint_id
        rec.blueprint_title = instance.blueprint_title
        rec.category = instance.category
        rec.icon = instance.icon
        rec.name = instance.name
        rec.owner_name = instance.owner_name
        rec.owner_email = instance.owner_email
        rec.team = instance.team
        rec.cost_center = instance.cost_center
        rec.environment = instance.environment.value if hasattr(instance.environment, "value") else str(instance.environment)
        rec.status = instance.status.value if hasattr(instance.status, "value") else str(instance.status)
        rec.progress_percentage = instance.progress_percentage
        rec.progress_message = instance.progress_message
        rec.created_at = instance.created_at
        rec.expires_at = instance.expires_at
        rec.ttl_days = instance.ttl_days
        rec.monthly_cost = instance.monthly_cost
        rec.endpoints = instance.endpoints
        rec.credentials = instance.credentials
        rec.parameters = instance.parameters
        rec.day2_actions = instance.day2_actions
        rec.logs = instance.logs

        db.commit()
    finally:
        db.close()


def remove_instance(instance_id: str) -> bool:
    db = SessionLocal()
    try:
        rec = db.query(InstanceRecord).filter(InstanceRecord.id == instance_id).first()
        if rec:
            db.delete(rec)
            db.commit()
            return True
        return False
    finally:
        db.close()


def log_audit(user_email: str, action: str, resource_id: str = None, details: str = None, ip_address: str = "127.0.0.1"):
    db = SessionLocal()
    try:
        log = AuditLog(
            user_email=user_email,
            action=action,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(log)
        db.commit()
    finally:
        db.close()
