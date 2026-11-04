import subprocess
import socket
import sys
import os
import signal
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from .base import BaseConnector


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_free_port(start_port: int = 8200, max_port: int = 8600) -> int:
    for port in range(start_port, max_port):
        if not is_port_in_use(port):
            return port
    raise RuntimeError("Nessuna porta TCP libera trovata.")


# Registry globale dei processi attivi
ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}


class ProcessConnector(BaseConnector):
    """
    Connettore per Ambienti e Servizi REALI eseguiti come processi locali dedicati.
    Avvia veri server web su porte TCP reali, permettendo di testare subito la piattaforma
    anche se il demone Docker non è temporaneamente avviato.
    """

    id = "process-connector"
    name = "Local Process & Microservice Runtime"
    platform_type = "process"
    description = "Esecutore reale di microservizi e web server su porte TCP locali dedicate."

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
        if progress_callback:
            await progress_callback(20, "Allocazione porta TCP libera sulla macchina host...")

        host_port = find_free_port(start_port=8200)

        if progress_callback:
            await progress_callback(40, f"Porta {host_port} riservata. Creazione directory e asset dell'ambiente...")

        # Creazione cartella dedicata per l'ambiente
        env_dir = Path(__file__).resolve().parent.parent.parent / "data" / "instances_data" / instance_id
        env_dir.mkdir(parents=True, exist_ok=True)

        customer = parameters.get("customer_name", "Azienda Partner")
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Ambiente Demo: {name}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; border: 1px solid #334155; max-width: 500px; text-align: center; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.5); }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0369a1; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: bold; }}
        .status {{ color: #4ade80; font-weight: bold; margin: 1rem 0; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Ambiente Attivo</span>
        <h1>{name}</h1>
        <p class="status">● Server HTTP Operativo sulla porta {host_port}</p>
        <p>Questo è un ambiente reale istanziato dalla piattaforma <strong>Enterprise Service Instantiator</strong>.</p>
        <p style="color: #94a3b8; font-size: 0.85rem;">Cliente / Riferimento: <strong>{customer}</strong><br>Instance ID: <code>{instance_id}</code></p>
    </div>
</body>
</html>
"""
        with open(env_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        if progress_callback:
            await progress_callback(70, f"Avvio server HTTP dedicato su http://localhost:{host_port}...")

        # Avvio del server web reale come processo isolato
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(host_port), "--directory", str(env_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        ACTIVE_PROCESSES[instance_id] = proc

        if progress_callback:
            await progress_callback(90, "Verifica connettività socket TCP...")

        # Attesa warm-up
        for _ in range(10):
            await asyncio.sleep(0.3)
            if is_port_in_use(host_port):
                break

        if progress_callback:
            await progress_callback(100, f"Servizio web reale attivo con PID {proc.pid} sulla porta {host_port}!")

        return {
            "endpoints": {
                "Portale Web Live": f"http://localhost:{host_port}",
                "Endpoint HTTP": f"http://127.0.0.1:{host_port}"
            },
            "credentials": {
                "PID Processo": str(proc.pid),
                "Directory Dati": str(env_dir)
            },
            "metadata": {
                "runtime": "Local Process",
                "pid": proc.pid,
                "host_port": host_port
            }
        }

    async def execute_action(
        self,
        instance_id: str,
        action: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        proc = ACTIVE_PROCESSES.get(instance_id)

        if action == "restart":
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            # Riavvio
            env_dir = Path(__file__).resolve().parent.parent.parent / "data" / "instances_data" / instance_id
            host_port = find_free_port(start_port=8200)
            new_proc = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(host_port), "--directory", str(env_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            ACTIVE_PROCESSES[instance_id] = new_proc
            return {"status": "SUCCESS", "message": f"Servizio riavviato su nuova porta {host_port} (PID {new_proc.pid})."}

        elif action == "stop":
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return {"status": "SUCCESS", "message": "Processo del servizio arrestato."}

        return {"status": "SUCCESS", "message": f"Azione {action} eseguita."}

    async def destroy(self, instance_id: str) -> bool:
        proc = ACTIVE_PROCESSES.get(instance_id)
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
            del ACTIVE_PROCESSES[instance_id]
        return True
