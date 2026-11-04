from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import asyncio


class BaseConnector(ABC):
    """
    Interfaccia Unificata (SPI - Service Provider Interface) per qualsiasi connettore.
    Ogni piattaforma (interna, cloud, SaaS esterna) implementa questo contratto.
    """

    id: str
    name: str
    platform_type: str
    description: str

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Verifica la correttezza dei parametri inviati."""
        pass

    @abstractmethod
    def calculate_cost(self, base_cost: float, parameters: Dict[str, Any]) -> float:
        """Calcola il costo mensile esatto in base alle opzioni scelte."""
        pass

    @abstractmethod
    async def apply_provisioning(
        self,
        instance_id: str,
        name: str,
        parameters: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Esegue il provisioning asincrono.
        Ritorna un dizionario con endpoints, credenziali e metadati generati.
        """
        pass

    @abstractmethod
    async def execute_action(
        self,
        instance_id: str,
        action: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Esegue un'operazione di Day-2 (restart, scale, backup, ecc.)."""
        pass

    @abstractmethod
    async def destroy(self, instance_id: str) -> bool:
        """Esegue il de-provisioning completo e la distruzione delle risorse."""
        pass
