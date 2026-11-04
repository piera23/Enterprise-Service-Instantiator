# Enterprise Service Instantiator (ESI) - Control Plane Enterprise v2.1

> Piattaforma Enterprise per DevOps & Platform Engineering: **Multi-Tenancy (Organizzazioni & Team)**, **Gestione Utenti (IAM) con 2FA TOTP**, **Database PostgreSQL 16**, **Blueprint Studio (creazione template senza codice)**, **Audit Trail immutabile** e **Wizard di provisioning dinamico non-pilotato**.

---

## 🏛️ Nuove Funzionalità Enterprise Implementate

### 1. Backoffice Amministrativo (IAM & Multi-Tenancy)
- **Gestione Utenti:** Creazione, modifica ruoli (`admin`, `devops_lead`, `developer`, `auditor`), assegnazione ai team, reset password e revoca/reset 2FA.
- **Gestione Team & Squad:** Ogni team ha il proprio **Centro di Costo**, **Team Lead** e **Budget Mensile FinOps** (con calcolo automatico del consumo percentuale e blocco quote).

### 2. Blueprint Studio (Crea Template Senza Toccare il Codice)
Gli amministratori e i DevOps Lead possono ora definire e pubblicare nuovi template self-service direttamente dall'interfaccia web:
- Titolo, icona, connettore runtime (`docker-connector`, `process-connector`, `k8s-adapter`), costo base e tempo stimato.
- **Aggiunta interattiva di campi di input dinamici:** tipo testo, select con opzioni e moltiplicatori di costo, flag obbligatorio e valori predefiniti.
- Il catalogo aziendale si aggiorna istantaneamente leggendo dal database relazionale PostgreSQL!

### 3. Wizard di Provisioning Dinamico in 4 Passi (Non-Pilotato)
1. **Contesto & Multi-Tenancy:** Selezione Team, Ambiente (`Dev`, `Staging`, `Prod`), Centro di Costo e Scadenza programmata (TTL).
2. **Parametri Tecnici Reali (dal Database):**
   - Per PostgreSQL: Nome DB, Sizing CPU/RAM, VPC/Rete aziendale (`VPC Rete Interna Sicura`, `VPC DMZ`, `VPC PCI-DSS`), Profilo Storage & IOPS (`gp3 SSD` o `io2 NVMe`), Policy di Backup (7, 30 o 90 giorni) e Classificazione Dati (`GDPR PII`, `Uso Interno`, `PCI Critici`).
3. **Variabili d'Ambiente & Secret Vault:** Aggiunta di coppie dinamiche chiave/valore e iniezione del path segreti HashiCorp Vault.
4. **FinOps & Approvazione:** Verifica capienza budget del team e instradamento automatico per approvazione SecOps/FinOps.

### 4. Audit Trail Immutabile
Tracciamento su database di ogni singola operazione (`USER_CREATED`, `TEAM_CREATED`, `BLUEPRINT_CREATED`, `PROVISIONING_STARTED`, `DAY2_RESTART`, `DESTROY`) con timestamp, utente, IP e dettagli.

---

## 🔐 Account Pre-Configurati per i Test

| Email | Password | Ruolo | Team di Appartenenza |
|---|---|---|---|
| `admin@azienda.com` | `AdminPass123!` | `admin` | Platform & DevOps Core |
| `devops.lead@azienda.com` | `DevOpsPass123!` | `devops_lead` | Platform & DevOps Core |
| `mario.rossi@azienda.com` | `DevPass123!` | `developer` | E-Commerce Squad |
| `laura.bianchi@azienda.com` | `DevPass123!` | `developer` | FinTech & Payments |

---

## 🚀 Avvio della Piattaforma

### Con Docker Compose (PostgreSQL 16 + Piattaforma)
```bash
docker compose up --build
```

### In Locale con Python (Server attualmente ATTIVO in background)
```powershell
.\.venv\Scripts\python.exe backend\run.py
```

- 🌐 **Portale Web & Backoffice:** [http://localhost:8080](http://localhost:8080)
- 📚 **Documentazione API Swagger:** [http://localhost:8080/docs](http://localhost:8080/docs)
