# Guida Completa al Debugging con Docker

Questa guida spiega in modo semplice e pratico come eseguire il debug della piattaforma **Enterprise Service Instantiator** e dei servizi gestiti tramite Docker.

---

## 1. Vedere i Log in Tempo Reale (La base del debug)

Se qualcosa non funziona o vuoi vedere cosa stampa il server durante una richiesta:

```bash
# Segui i log di tutta la piattaforma in tempo reale (streaming continuo):
docker compose logs -f

# Segui solo i log del backend dell'istanziatore:
docker compose logs -f istanziatore

# Segui solo i log del database PostgreSQL:
docker compose logs -f postgres
```

---

## 2. Hot-Reloading: Modificare il Codice Senza Ri-buildare

Nel `docker-compose.yml` abbiamo configurato i volumi mappati:
- `./backend:/app/backend`
- `./frontend:/app/frontend`

**Cosa significa?**  
Non serve rilanciare `docker compose build` ogni volta che modifichi un file. Quando modifichi qualsiasi file Python o HTML nel tuo editor (VS Code, Cursor, PyCharm), **Uvicorn rileva la modifica e ricarica il codice istantaneamente (in 0.2 secondi)** direttamente dentro Docker!

---

## 3. Debug con Breakpoint Interattivi da VS Code (Tasto F5)

Nel `docker-compose.yml` è attiva la porta **`5678`** con `debugpy` (il debugger standard di Python).

Abbiamo già creato il file di configurazione [`.vscode/launch.json`](.vscode/launch.json).

### Come usarlo:
1. Avvia i container:
   ```bash
   docker compose up
   ```
2. Apri VS Code in questa cartella.
3. Vai nella sezione **"Esegui e debug"** (icona a forma di insetto sulla barra sinistra di VS Code, oppure premi `Ctrl+Shift+D`).
4. Seleziona dal menu in alto: **`Docker: Attach al Container (F5)`** e premi il tasto verde di avvio (o premi **`F5`**).
5. Metti un punto rosso (breakpoint) su qualsiasi riga di codice (es. in `backend/app/routers/auth_routes.py` o in `backend/app/connectors/docker_connector.py`).
6. Fai una chiamata dal browser: **il codice si fermerà esattamente su quella riga**, permettendoti di ispezionare le variabili, avanzare passo-passo (F10) ed eseguire comandi nella console di debug!

---

## 4. Entrare Dentro il Container (Shell Interattiva)

Per verificare i file interni, testare comandi o controllare le variabili d'ambiente dall'interno del container:

```bash
# Apri una shell bash dentro il container dell'istanziatore:
docker exec -it esi-platform bash

# Esempio: verifica che la CLI Docker dentro il container veda il demone dell'host:
docker ps
```

### Ispezionare direttamente il Database PostgreSQL:
Per eseguire query SQL dirette dentro il database:
```bash
docker exec -it esi-postgres psql -U esi_admin -d esi_database

# Comandi utili psql:
# \dt          -> Elenco di tutte le tabelle (users, instances, audit_logs)
# SELECT * FROM users;
# SELECT id, name, status, monthly_cost FROM instances;
# \q          -> Esci
```

---

## 5. Debug dei Container Istanziati dalla Piattaforma

Quando un utente clicca *"Istanzia"* sul portale (es. per un Database PostgreSQL o un Web Server Nginx), la piattaforma crea un container reale sull'host.

### Come trovarli da terminale:
```bash
# Elenco di tutti i container creati dall'istanziatore:
docker ps --filter "label=managed-by=enterprise-service-instantiator"

# Visualizza i log di uno specifico container istanziato:
docker logs -f esi_inst_xxxx

# Riavvia forzatamente il container:
docker restart esi_inst_xxxx

# Verifica la porta TCP su cui sta rispondendo:
docker port esi_inst_xxxx
```
