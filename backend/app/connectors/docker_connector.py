# ==============================================================================
# DOCKER_CONNECTOR.PY - Connettore Reale a Docker Engine
# Esegue container reali, riserva porte TCP dinamiche, inietta credenziali e gestisce il lifecycle
# ==============================================================================

# Esecuzione di processi di sistema e comandi CLI Docker sincroni/asincroni
import subprocess
# Interazione a basso livello con socket di rete per testare la disponibilità delle porte TCP
import socket
# Serializzazione/deserializzazione di dati in formato JSON
import json
# Misurazione dei tempi e pause
import time
# Programmazione concorrente asincrona per non bloccare l'event loop di FastAPI
import asyncio
# Tipizzazione Python per collezioni e valori opzionali
from typing import Dict, Any, Tuple, Optional, List
# Classe base astratta per connettori
from .base import BaseConnector


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    Verifica se una porta TCP è già occupata su un determinato host.
    Tenta una connessione socket TCP: se il connect ha successo (codice 0), la porta è occupata.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        # connect_ex restituisce 0 se la connessione è riuscita (porta aperta/occupata)
        return s.connect_ex((host, port)) == 0


def find_free_port(start_port: int = 8100, max_port: int = 8500) -> int:
    """
    Scansiona sequenzialmente un intervallo di porte TCP sull'host locale
    e restituisce la prima porta libera disponibile per il mapping del container.
    """
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    # Se nessuna porta è disponibile nell'intervallo specificato
    raise RuntimeError("Nessuna porta TCP libera trovata nell'intervallo specificato.")


def run_command_sync(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    """
    Esegue in modo sincrono e sicuro un comando esterno sul sistema operativo (es. CLI docker).
    Restituisce una tupla (returncode, stdout, stderr).
    """
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False # Evita l'uso della shell per prevenire vulnerabilità di shell injection
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        # In caso di eccezione (es. timeout o comando non trovato), restituisce codice -1
        return -1, "", str(e)


class DockerConnector(BaseConnector):
    """
    Connettore REALE a Docker Engine.
    Interroga il Docker daemon (via CLI o socket DooD) ed esegue container reali,
    gestisce porte dinamiche, volumi, variabili d'ambiente, log e ciclo di vita.
    """

    id = "docker-connector"
    name = "Docker Engine Orchestrator"
    platform_type = "container"
    description = "Orchestratore reale di container Docker con porte dinamiche e controllo salute in tempo reale."

    def is_docker_available(self) -> bool:
        """Verifica se il demone Docker è raggiungibile eseguendo 'docker info'."""
        code, out, _ = run_command_sync(["docker", "info"])
        return code == 0

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Verifica la correttezza dei parametri inviati."""
        return True, "Parametri validi"

    def calculate_cost(self, base_cost: float, parameters: Dict[str, Any]) -> float:
        """Calcola il costo del container; opzionalmente applica moltiplicatori."""
        return round(base_cost, 2)

    async def apply_provisioning(
        self,
        instance_id: str,
        name: str,
        parameters: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Esegue il provisioning reale di un container Docker.
        Scarica l'immagine (se non presente), riserva una porta libera dell'host,
        avvia il container in background e ne verifica il warm-up.
        """
        # Estrazione del tipo di servizio richiesto (default: web)
        service_type = parameters.get("service_type", "web")
        # Generazione di un nome univoco e valido per il container Docker
        container_name = f"esi_{instance_id.replace('-', '_')}"

        # Controllo preventivo della disponibilità del demone Docker
        if not self.is_docker_available():
            raise RuntimeError(
                "Docker Daemon non raggiungibile. Assicurati che Docker Desktop o il demone Docker siano avviati, "
                "oppure esegui la piattaforma tramite 'docker compose up'."
            )

        # Notifica avanzamento: ricerca porta
        if progress_callback:
            await progress_callback(15, "Ricerca porta host libera per il container...")

        # Assegnazione porta dinamica e scelta dell'immagine Docker in base al servizio
        target_internal_port = 80
        if service_type == "postgres":
            target_internal_port = 5432
            image = "postgres:16-alpine"
        elif service_type == "redis":
            target_internal_port = 6379
            image = "redis:alpine"
        else:
            target_internal_port = 80
            image = "nginx:alpine"

        # Ricerca della prima porta libera a partire dalla 8100
        host_port = find_free_port(start_port=8100)

        # Notifica avanzamento: download immagine
        if progress_callback:
            await progress_callback(30, f"Porta {host_port} riservata. Download/Pull immagine {image}...")

        # Esecuzione del 'docker pull' in un thread separato per non bloccare l'event loop asincrono
        await asyncio.to_thread(run_command_sync, ["docker", "pull", image], 60)

        if progress_callback:
            await progress_callback(60, f"Avvio container Docker '{container_name}'...")

        # Composizione degli argomenti del comando 'docker run -d'
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{host_port}:{target_internal_port}",
            "-l", "managed-by=enterprise-service-instantiator",
            "-l", f"instance-id={instance_id}"
        ]

        credentials = {}
        endpoints = {}

        # Configurazione specifica per database PostgreSQL
        if service_type == "postgres":
            db_name = parameters.get("db_name", "enterprise_db")
            db_user = parameters.get("db_user", "esi_admin")
            db_pass = parameters.get("db_pass", f"PgSec_{instance_id[-6:]}!")
            cmd.extend([
                "-e", f"POSTGRES_DB={db_name}",
                "-e", f"POSTGRES_USER={db_user}",
                "-e", f"POSTGRES_PASSWORD={db_pass}",
            ])
            credentials = {
                "Host": "localhost",
                "Porta": str(host_port),
                "Database": db_name,
                "Username": db_user,
                "Password": db_pass,
                "Connection URI": f"postgresql://{db_user}:{db_pass}@localhost:{host_port}/{db_name}"
            }
            endpoints = {
                "JDBC Connection": f"jdbc:postgresql://localhost:{host_port}/{db_name}",
                "Host TCP": f"localhost:{host_port}"
            }

        # Configurazione specifica per cache in-memory Redis
        elif service_type == "redis":
            credentials = {
                "Host": "localhost",
                "Porta": str(host_port),
                "Protocol": "RESP (Redis)"
            }
            endpoints = {
                "Redis URI": f"redis://localhost:{host_port}",
                "Host TCP": f"localhost:{host_port}"
            }

        # Configurazione di default: server web Nginx o reverse proxy
        else:
            customer = parameters.get("customer_name", "Azienda Partner")
            endpoints = {
                "Portale Web Live": f"http://localhost:{host_port}",
                "Endpoint HTTP": f"http://127.0.0.1:{host_port}"
            }
            credentials = {
                "Accesso": "Anonimo / Demo Pubblica",
                "Tipo Container": "Nginx Alpine Live Server"
            }

        # Aggiunta dell'immagine come ultimo argomento
        cmd.append(image)

        # Esecuzione del comando di avvio del container
        code, container_id, err = await asyncio.to_thread(run_command_sync, cmd, 30)
        if code != 0:
            raise RuntimeError(f"Errore avvio container Docker: {err}")

        if progress_callback:
            await progress_callback(85, "Attesa warm-up e healthcheck sulla porta TCP...")

        # Attesa del warm-up del servizio con polling rapido sulla porta assegnata
        attempts = 0
        while attempts < 10:
            await asyncio.sleep(0.5)
            if is_port_in_use(host_port):
                break
            attempts += 1

        if progress_callback:
            await progress_callback(100, f"Container attivo con ID {container_id[:12]} sulla porta {host_port}!")

        # Restituzione del dizionario con tutti i metadati e gli endpoint operativi
        return {
            "endpoints": endpoints,
            "credentials": credentials,
            "metadata": {
                "runtime": "Docker",
                "container_id": container_id[:12],
                "container_name": container_name,
                "image": image,
                "host_port": host_port,
                "internal_port": target_internal_port
            }
        }

    async def execute_action(
        self,
        instance_id: str,
        action: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Esegue operazioni di gestione Day-2 sul container Docker:
        - 'restart': riavvia il container
        - 'stop': arresta temporaneamente il container
        - 'start': riavvia un container precedentemente arrestato
        - 'live_logs': estrae gli ultimi 60 log del container
        """
        container_name = f"esi_{instance_id.replace('-', '_')}"

        if action == "restart":
            code, _, err = await asyncio.to_thread(run_command_sync, ["docker", "restart", container_name], 20)
            if code != 0:
                raise RuntimeError(f"Errore riavvio container: {err}")
            return {"status": "SUCCESS", "message": f"Container Docker '{container_name}' riavviato con successo."}

        elif action == "stop":
            code, _, err = await asyncio.to_thread(run_command_sync, ["docker", "stop", container_name], 20)
            if code != 0:
                raise RuntimeError(f"Errore arresto container: {err}")
            return {"status": "SUCCESS", "message": f"Container Docker '{container_name}' arrestato."}

        elif action == "start":
            code, _, err = await asyncio.to_thread(run_command_sync, ["docker", "start", container_name], 20)
            if code != 0:
                raise RuntimeError(f"Errore avvio container: {err}")
            return {"status": "SUCCESS", "message": f"Container Docker '{container_name}' avviato."}

        elif action == "live_logs":
            code, logs, err = await asyncio.to_thread(run_command_sync, ["docker", "logs", "--tail", "60", container_name], 10)
            return {"status": "SUCCESS", "logs": logs if code == 0 else err}

        return {"status": "SUCCESS", "message": f"Azione {action} completata."}

    async def destroy(self, instance_id: str) -> bool:
        """
        Esegue la distruzione forzata e rimozione del container associato all'istanza ('docker rm -f').
        """
        container_name = f"esi_{instance_id.replace('-', '_')}"
        code, _, _ = await asyncio.to_thread(run_command_sync, ["docker", "rm", "-f", container_name], 20)
        return code == 0
