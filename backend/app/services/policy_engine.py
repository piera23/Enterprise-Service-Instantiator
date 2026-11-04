from typing import Tuple
from ..models import ProvisionRequest, Blueprint, InstanceStatus, EnvironmentEnum


class PolicyEngine:
    """
    Motore di regole e guardrails aziendali.
    Determina se una richiesta è conforme, auto-approvata o necessita di autorizzazione.
    """

    @staticmethod
    def evaluate(blueprint: Blueprint, request: ProvisionRequest, calculated_cost: float) -> Tuple[bool, InstanceStatus, str]:
        # 1. Validazione ambiente di produzione
        if request.environment == EnvironmentEnum.PROD:
            return True, InstanceStatus.APPROVAL_REQUIRED, "Richiesta per ambiente di PRODUZIONE: inoltrata approvazione a SecOps e Release Manager."

        # 2. Controllo soglia di budget / FinOps
        if calculated_cost > blueprint.auto_approval_limit_eur:
            return True, InstanceStatus.APPROVAL_REQUIRED, (
                f"Il costo mensile stimato (€{calculated_cost:.2f}) supera la soglia di auto-approvazione "
                f"(€{blueprint.auto_approval_limit_eur:.2f}). Inviata notifica di autorizzazione al Team Lead."
            )

        # 3. Controllo TTL massimo per ambienti di test
        if request.environment == EnvironmentEnum.DEV and request.ttl_days > 60:
            return True, InstanceStatus.APPROVAL_REQUIRED, "TTL superiore a 60 giorni per ambiente DEV: richiesta deroga al responsabile di reparto."

        # Auto-approvato
        return True, InstanceStatus.PENDING, "Richiesta pienamente conforme alle policy aziendali. Auto-approvazione concessa!"
