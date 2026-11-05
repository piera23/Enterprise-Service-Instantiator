# ==============================================================================
# DOCKERFILE - Enterprise Service Instantiator (ESI)
# Immagine di base ufficiale Python 3.11 su Debian Slim per minimizzare la superficie di attacco e il peso
# ==============================================================================
FROM python:3.11-slim

# Aggiornamento dell'indice dei pacchetti e installazione di certificati e strumenti di download
# --no-install-recommends evita l'installazione di pacchetti raccomandati ma non indispensabili
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    # Creazione della cartella per le chiavi GPG di APT con permessi ristretti (0755)
    && install -m 0755 -d /etc/apt/keyrings \
    # Download della chiave GPG ufficiale di Docker per verificare l'integrità dei pacchetti
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    # Assegnazione dei permessi di lettura alla chiave GPG per tutti gli utenti
    && chmod a+r /etc/apt/keyrings/docker.asc \
    # Aggiunta del repository ufficiale di Docker ai sorgenti APT di Debian
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    # Installazione del Docker CE CLI (Command Line Interface) per comunicare con il demone Docker dell'host (DooD)
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    # Pulizia della cache APT per mantenere il container il più snello possibile
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Definizione della directory di lavoro principale all'interno del container
WORKDIR /app

# Copia esclusiva del file dei requisiti per sfruttare la cache dei layer Docker in caso di modifiche al codice
COPY backend/requirements.txt /app/backend/requirements.txt

# Installazione delle librerie Python (FastAPI, SQLAlchemy, Uvicorn, psycopg2, pyotp, ecc.) senza cache locale
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copia dell'albero sorgente del backend
COPY backend/ /app/backend/

# Copia delle risorse statiche e single-page application del frontend
COPY frontend/ /app/frontend/

# Creazione della directory dedicata alla persistenza dei dati (database SQLite di fallback, file JSON, asset)
RUN mkdir -p /app/backend/data

# Esposizione della porta 8080 su cui Uvicorn accetta le connessioni HTTP
EXPOSE 8080

# Comando di avvio del servizio all'avvio del container: esecuzione del runner Python
CMD ["python", "backend/run.py"]
