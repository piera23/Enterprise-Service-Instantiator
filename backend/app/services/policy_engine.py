# ==============================================================================
# POLICY_ENGINE.PY - Motore Guardrails FinOps e Governance Aziendale
# Valida le richieste in base all'ambiente, budget e TTL, decidendo l'auto-approvazione
# ==============================================================================

# Tipizzazione Python per tuple
from typing import Tuple
# Modelli Pydantic per richieste, blueprint, stati e ambienti
from ..models import ProvisionRequest, Blueprint, InstanceStatus, EnvironmentEnum


class PolicyEngine:
    """
    Motore di regole e guardrails aziendali (Policy as Code).
    Determina se una richiesta di provisioning è pienamente conforme e auto-approvata,
    oppure se richiede un'approvazione formale da parte di SecOps, Team Lead o Release Manager.
    """

    @staticmethod
    def evaluate(blueprint: Blueprint, request: ProvisionRequest, calculated_cost: float) -> Tuple[bool, InstanceStatus, str]:
        """
        Valuta i vincoli di governance aziendale sulla richiesta:
        1. Regola Produzione: Qualsiasi risorsa per 'prod' richiede autorizzazione obbligatoria.
        2. Regola FinOps: Se il costo mensile calcolato supera la soglia del template, richiede autorizzazione.
        3. Regola TTL Dev: Se un ambiente di sviluppo richiede più di 60 giorni, richiede autorizzazione.
        4. In assenza di violazioni: Concessione immediata dell'auto-approvazione (PENDING).
        """
        # 1. Validazione ambiente di produzione: obbligo di approvazione preventiva
        if request.environment == EnvironmentEnum.PROD:
            return True, InstanceStatus.APPROVAL_REQUIRED, "Richiesta per ambiente di PRODUZIONE: inoltrata approvazione a SecOps e Release Manager."

        # 2. Controllo soglia di budget FinOps: confronto con il limite consentito dal Blueprint
        if calculated_cost > blueprint.auto_approval_limit_eur:
            return True, InstanceStatus.APPROVAL_REQUIRED, (
                f"Il costo mensile stimato (€{calculated_cost:.2f}) supera la soglia di auto-approvazione "
                f"(€{blueprint.auto_approval_limit_eur:.2f}). Inviata notifica di autorizzazione al Team Lead."
            )

        # 3. Controllo TTL massimo per ambienti di test e sviluppo (massimo 60 giorni)
        if request.environment == EnvironmentEnum.DEV and request.ttl_days > 60:
            return True, InstanceStatus.APPROVAL_REQUIRED, "TTL superiore a 60 giorni per ambiente DEV: richiesta deroga al responsabile di reparto."

        # 4. Richiesta pienamente conforme alle policy aziendali: auto-approvata
        return True, InstanceStatus.PENDING, "Richiesta pienamente conforme alle policy aziendali. Auto-approvazione concessa!"
