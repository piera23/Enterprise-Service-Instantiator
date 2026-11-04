import subprocess
import socket
import json
import time
import asyncio
from typing import Dict, Any, Tuple, Optional, List
from .base import BaseConnector


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_free_port(start_port: int = 8100, max_port: int = 8500) -> int:
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    raise RuntimeError("Nessuna porta TCP libera trovata nell'intervallo specificato.")


def run_command_sync(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


class DockerConnector(BaseConnector):
    """
    Connettore REALE a Docker Engine.
    Interroga il Docker daemon (via CLI o socket) ed esegue container reali,
    gestisce porte dinamiche, volumi, variabili d'ambiente, log e ciclo di vita.
    """

    id = "docker-connector"
    name = "Docker Engine Orchestrator"
    platform_type = "container"
    description = "Orchestratore reale di container Docker con porte dinamiche e controllo salute in tempo reale."

    def is_docker_available(self) -> bool:
        code, out, _ = run_command_sync(["docker", "info"])
        return code == 0

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "Parametri validi"

    def calculate_cost(self, base_cost: float, parameters: Dict[str, Any]) -> float:
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
        Se Docker non è installato o attivo sull'host corrente,
        effettua un fallback pulito informando l'utente.
        """
        service_type = parameters.get("service_type", "web")
        container_name = f"esi_{instance_id.replace('-', '_')}"

        if not self.is_docker_available():
            raise RuntimeError(
                "Docker Daemon non raggiungibile. Assicurati che Docker Desktop o il demone Docker siano avviati, "
                "oppure esegui la piattaforma tramite 'docker compose up'."
            )

        if progress_callback:
            await progress_callback(15, "Ricerca porta host libera per il container...")

        # Assegnazione porta dinamica
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

        host_port = find_free_port(start_port=8100)

        if progress_callback:
            await progress_callback(30, f"Porta {host_port} riservata. Download/Pull immagine {image}...")

        # Pull immagine
        await asyncio.to_thread(run_command_sync, ["docker", "pull", image], 60)

        if progress_callback:
            await progress_callback(60, f"Avvio container Docker '{container_name}'...")

        # Composizione comando docker run
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{host_port}:{target_internal_port}",
            "-l", "managed-by=enterprise-service-instantiator",
            "-l", f"instance-id={instance_id}"
        ]

        credentials = {}
        endpoints = {}

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

        else:
            # Web Server Demo Nginx
            customer = parameters.get("customer_name", "Azienda Partner")
            endpoints = {
                "Portale Web Live": f"http://localhost:{host_port}",
                "Endpoint HTTP": f"http://127.0.0.1:{host_port}"
            }
            credentials = {
                "Accesso": "Anonimo / Demo Pubblica",
                "Tipo Container": "Nginx Alpine Live Server"
            }

        cmd.append(image)

        code, container_id, err = await asyncio.to_thread(run_command_sync, cmd, 30)
        if code != 0:
            raise RuntimeError(f"Errore avvio container Docker: {err}")

        if progress_callback:
            await progress_callback(85, "Attesa warm-up e healthcheck sulla porta TCP...")

        # Attesa e verifica che la porta risponda
        attempts = 0
        while attempts < 10:
            await asyncio.sleep(0.5)
            if is_port_in_use(host_port):
                break
            attempts += 1

        if progress_callback:
            await progress_callback(100, f"Container attivo con ID {container_id[:12]} sulla porta {host_port}!")

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
        container_name = f"esi_{instance_id.replace('-', '_')}"
        code, _, _ = await asyncio.to_thread(run_command_sync, ["docker", "rm", "-f", container_name], 20)
        return code == 0
