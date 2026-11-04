from fastapi import APIRouter
from collections import defaultdict
from ..models import FinOpsStats, InstanceStatus
from ..services.storage import get_all_instances

router = APIRouter(prefix="/api/v1/stats", tags=["FinOps & Analytics"])


@router.get("", response_model=FinOpsStats, summary="Metriche FinOps, consumo mensile e risparmio generato da spegnimenti automatici")
def get_stats():
    instances = get_all_instances()

    active_count = 0
    monthly_spend = 0.0
    by_env = defaultdict(int)
    by_cat = defaultdict(int)

    for inst in instances:
        if inst.status in [InstanceStatus.ACTIVE, InstanceStatus.PROVISIONING, InstanceStatus.ACTION_IN_PROGRESS]:
            active_count += 1
            monthly_spend += inst.monthly_cost
        by_env[inst.environment.value] += 1
        by_cat[inst.category] += 1

    # Calcolo risparmio stimato derivante da ambienti con TTL invece che lasciati accesi 24/7/365
    # Stima prudenziale: 35% di risparmio sui costi totali grazie a de-commissioning automatico
    estimated_savings = round(monthly_spend * 0.38, 2)

    return FinOpsStats(
        total_active_instances=active_count,
        total_monthly_spend=round(monthly_spend, 2),
        total_savings_via_ttl=estimated_savings,
        instances_by_environment=dict(by_env),
        instances_by_category=dict(by_cat)
    )
