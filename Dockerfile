FROM python:3.11-slim

# Installazione Docker CLI per consentire al container di comunicare con il demone Docker dell'host
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e installazione requisiti Python
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copia del codice backend e frontend
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Directory per la persistenza dei dati
RUN mkdir -p /app/backend/data

EXPOSE 8080

CMD ["python", "backend/run.py"]
