# ==============================================================================
# BASE.PY - Interfaccia Astratta Unificata dei Connettori (SPI)
# Definisce il contratto standard che ogni connettore (Docker, K8s, Cloud, ecc.) deve rispettare
# ==============================================================================

# Modulo standard per la definizione di classi e metodi astratti (Abstract Base Classes)
from abc import ABC, abstractmethod
# Tipizzazione Python per strutture complesse e tuple
from typing import Dict, Any, Tuple
# Supporto alla programmazione concorrente asincrona
import asyncio


class BaseConnector(ABC):
    """
    Interfaccia Unificata (SPI - Service Provider Interface) per qualsiasi connettore.
    Ogni piattaforma sottostante (Docker locale, processo OS, cluster Kubernetes, Cloud Provider o SaaS)
    implementa questo contratto standard per garantire totale disaccoppiamento tra il catalogo e l'infrastruttura.
    """

    # Identificativo univoco del connettore (es. "docker-connector")
    id: str
    # Nome visualizzato nella console e nei log (es. "Docker Engine Orchestrator")
    name: str
    # Tipologia di piattaforma: "container", "process", "cloud", "database", "kubernetes", "saas"
    platform_type: str
    # Descrizione estesa delle funzionalità e della modalità di provisioning
    description: str

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida i parametri inviati dall'utente prima di avviare il provisioning.
        Restituisce una tupla (valido: bool, messaggio_errore: str).
        """
        pass

    @abstractmethod
    def calculate_cost(self, base_cost: float, parameters: Dict[str, Any]) -> float:
        """
        Calcola l'esatto costo mensile in Euro tenendo conto delle opzioni scelte
        (es. dimensionamento CPU/RAM, policy di backup, retention o repliche).
        """
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
        Esegue il provisioning asincrono delle risorse infrastrutturali.
        Durante l'elaborazione può invocare progress_callback(percentuale, messaggio) per aggiornare lo stato.
        Restituisce un dizionario contenente endpoints, credentials e metadata della risorsa creata.
        """
        pass

    @abstractmethod
    async def execute_action(
        self,
        instance_id: str,
        action: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Esegue un'operazione di gestione Day-2 sulla risorsa (es. restart, stop, start, backup, scale).
        Restituisce un dizionario con l'esito dell'operazione.
        """
        pass

    @abstractmethod
    async def destroy(self, instance_id: str) -> bool:
        """
        Esegue il de-provisioning completo, arrestando e deallocando definitivamente tutte le risorse assegnate
        (container, processi, porte TCP, cartelle temporanee, ecc.).
        """
        pass
