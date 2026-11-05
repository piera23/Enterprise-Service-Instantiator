# ==============================================================================
# ROUTERS/STATS.PY - Router API FinOps, Consumi di Budget e Risparmi TTL
# Calcola metriche aggregate in tempo reale: spesa mensile, ripartizioni e risparmio
# ==============================================================================

# Costruttore del router di FastAPI
from fastapi import APIRouter
# Dizionario con valore predefinito per conteggi statistici
from collections import defaultdict
# Schemi Pydantic per statistiche FinOps e stati delle istanze
from ..models import FinOpsStats, InstanceStatus
# Query per recuperare tutte le istanze dal database
from ..services.storage import get_all_instances

# Istanziazione del router con prefisso di percorso e tag OpenAPI
router = APIRouter(prefix="/api/v1/stats", tags=["FinOps & Analytics"])


@router.get("", response_model=FinOpsStats, summary="Metriche FinOps, consumo mensile e risparmio generato da spegnimenti automatici")
def get_stats():
    """
    Analizza tutte le istanze per calcolare:
    - Numero di risorse attive o in provisioning
    - Spesa totale mensile corrente
    - Ripartizione per ambiente (dev, staging, prod)
    - Ripartizione per categoria architetturale
    - Risparmio stimato ottenuto spegnendo le risorse tramite TTL programmato
    """
    instances = get_all_instances()

    active_count = 0
    monthly_spend = 0.0
    by_env = defaultdict(int)
    by_cat = defaultdict(int)

    # Itera su tutte le istanze aggregate
    for inst in instances:
        # Se l'istanza è attiva o in fase di avvio/azione, concorre alla spesa computata
        if inst.status in [InstanceStatus.ACTIVE, InstanceStatus.PROVISIONING, InstanceStatus.ACTION_IN_PROGRESS]:
            active_count += 1
            monthly_spend += inst.monthly_cost
        # Raggruppa il conteggio per ambiente e categoria
        by_env[inst.environment.value] += 1
        by_cat[inst.category] += 1

    # Calcolo del risparmio FinOps stimato derivante dall'adozione del Time-To-Live (TTL):
    # Rispetto a macchine e cluster lasciati accesi 24/7/365, lo spegnimento automatico
    # genera in media un abbattimento prudenziale del 38% sui costi di infrastruttura
    estimated_savings = round(monthly_spend * 0.38, 2)

    return FinOpsStats(
        total_active_instances=active_count,
        total_monthly_spend=round(monthly_spend, 2),
        total_savings_via_ttl=estimated_savings,
        instances_by_environment=dict(by_env),
        instances_by_category=dict(by_cat)
    )
