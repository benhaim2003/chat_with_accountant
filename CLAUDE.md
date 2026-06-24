# Project Context: Chat with Accountant

## 1. Project Overview
"Chat with Accountant" is an automated messaging and file-handling system designed for a Certified Public Accountant (CPA) office — **רבינוביץ אבן ממן**. The ultimate goal of the project is to:
* Streamline how the office handles routine client requests.
* Reduce the administrative burden on the secretariat.
* Improve client response times through an easy-to-use chat interface.

The project is structured into three distinct development phases: **Proof of Concept (POC)** ✅, **Minimum Viable Product (MVP)** 🔄, and **Next Stage (AI Integration)**.

### Architectural Philosophy: Forward Compatibility
A core requirement of this project is zero technical debt. The transition between phases must be a seamless evolution, not a complete rewrite. The codebase must be modular from day one—specifically anticipating the future addition of new platforms (WhatsApp), database-driven authentication, and LLM endpoints.

---

## 2. Phase 1: Proof of Concept (POC) — COMPLETE ✅

### What was built
A working Telegram bot that bridges client messages to the CPA office email system and routes secretary replies back to the client.

### Tech Stack
| Component | Technology |
| :--- | :--- |
| Messaging platforms | Telegram (`python-telegram-bot>=22.0`), WhatsApp Cloud API (FastAPI webhook) |
| Email | Microsoft Graph API (app-only auth via MSAL) |
| Session & thread storage | Redis (`redis>=5.0.0`) |
| Runtime | Python 3.12+ |

---

## 3. Phase 2: Minimum Viable Product (MVP) — IN PROGRESS 🔄

### What was built so far
* Full button-driven FSM with 3 options (1/2/3) — option ד (other) removed
* File upload flow with optional description (option 1)
* File request flow (option 2)
* One-shot message-to-accountant flow (option 3)
* After each completed flow: "send another / main menu / close" buttons
* Client-initiated `/close` command (silent escape hatch; not advertised in the UI)
* Pilot client identification via hardcoded chat_id → name map in `src/repositories/pilot_clients.py`
* WhatsApp adapter — **live in production** via WhatsApp Business Cloud API on the bot's registered WhatsApp number (set in `.env`, not committed)
* Docker containerization (`Dockerfile` + `.dockerignore`)
* Azure Container Apps deployment (`deploy.ps1`) — bot is **live in production**

### WhatsApp Status
`src/adapters/whatsapp_adapter.py` is active. The FastAPI webhook starts inside the container on port 8080 whenever `WHATSAPP_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID` / `WHATSAPP_VERIFY_TOKEN` are all set. Azure Container Apps exposes it externally via HTTPS ingress; Meta's webhook points at `https://<container-app-fqdn>/webhook/whatsapp` (the FQDN is shown by `deploy.ps1` after a successful deploy, also retrievable via `az containerapp show`).

### Codebase Structure
```
src/
  adapters/
    base.py                  # PlatformAdapter ABC (send_text / send_response / send_file / start)
    telegram_adapter.py      # Telegram bot; inline keyboards + CallbackQueryHandler for button taps
    whatsapp_adapter.py      # WhatsApp Cloud API; FastAPI webhook + interactive buttons (live)
  core/
    menu_handler.py          # FSM: routes messages through 7 states; returns MenuResponse
    message_router.py        # Dispatches InternalMessage to MenuHandler; handle_close()
    session_manager.py       # Redis-backed session store (key: session:{platform}:{chat_id})
  infrastructure/
    redis_client.py          # Singleton get_redis() — reads REDIS_URL from env
  models/
    internal_message.py      # InternalMessage + Platform/MessageType enums (TEXT, BUTTON, DOCUMENT, PHOTO)
    menu_response.py         # MenuResponse(text, buttons=(MenuButton(label, payload), …))
    user_model.py            # UserSession dataclass (persisted to Redis as JSON)
    client.py                # Client + Contact dataclasses
  repositories/
    client_repository.py     # Loads clients from data/clients.json (MVP: replace with DB)
    pilot_clients.py         # Pilot-phase chat_id → display-name dict (used in email subjects)
  services/
    email_gateway.py         # GraphEmailGateway — send/poll via Microsoft Graph
    file_handler.py          # Saves incoming files to /tmp/cpa_bot_uploads/
  main.py                    # Wires everything together; on_secretary_reply callback
Dockerfile                   # python:3.12-slim; CMD ["python", "-m", "src.main"]
.dockerignore
deploy.ps1                   # Azure Container Apps deploy (commit-hash image tag; opt-in WhatsApp + ingress)
config.py                    # Root-level logging config
```

### Session State Machine
| State | Meaning |
| :--- | :--- |
| `idle` | No active session — next message shows the menu |
| `awaiting_option` | Menu shown, waiting for the user to tap one of the three buttons (payloads "1"/"2"/"3") |
| `awaiting_file_upload` | Waiting for client to upload a document (option 1) |
| `awaiting_description_choice` | File received, asking if client wants to add a description |
| `awaiting_description` | Waiting for client to type the description text |
| `awaiting_file_request` | Waiting for client to describe which file they need (option 2) |
| `awaiting_accountant_message` | Waiting for the client's message to the accountant (option 3) |
| `awaiting_followup_decision` | A one-shot flow just completed; client prompted to send another, return to main menu, or close |

### Menu & Option Flows

**Option 1 — Upload document:**
1. Ask client to send file
2. File received → ask "add description? כן/לא" (buttons)
3. If yes → ask for description text
4. Send email with file + optional description → set `awaiting_followup_decision`

**Option 2 — Request a file:**
1. Ask client to describe the file they need
2. Send email with request → set `awaiting_followup_decision`

**Option 3 — Message to accountant:**
1. Client sends a single message → send email → set `awaiting_followup_decision`

**Follow-up after each completed flow:** three contextual buttons — "send another" (re-enters the same flow's input state), "main menu", "close".

**Secretary reply:**
- Poller forwards body + attachments straight to the client. No close marker — clients end the conversation themselves with the close button.

**Client `/close` command:**
- Routes: `TelegramAdapter._on_close` → `MessageRouter.handle_close` → `MenuHandler.handle_close` → `session_manager.clear_session`
- Silent escape hatch for free-text states; not mentioned in the menu UI.

### Redis Key Conventions
| Key | Value | TTL |
| :--- | :--- | :--- |
| `session:{platform}:{chat_id}` | JSON-serialized `UserSession` | 24 h (reset on every write) |
| `thread:{conversationId}` | `platform:chat_id` (e.g. `telegram:123456`) | 7 days |

### Email Bridge
1. Client interaction → `GraphEmailGateway.send()` creates draft, attaches file if any, sends, stores `thread:{conversationId} → platform:chat_id` in Redis. Subjects are `[CPA Bot] {client_label} · {action}` so the secretary can scan the inbox.
2. Poller (every 30 s) reads unread inbox messages, matches `conversationId` → `platform:chat_id` via Redis.
3. Strips quoted history from the reply body.
4. `on_secretary_reply` callback in `main.py` forwards text + attachments to the client. No close-marker plumbing — closing the conversation is the client's responsibility (via the close button or `/close`).

### Email Body Stripping
`GraphEmailGateway._extract_body` strips:
- Quoted text starting with `On ... wrote:` (English clients)
- Hebrew quoted text starting with `בתאריך` (pattern: `(?:^|\n)[‎‏‪-‮‫⁦-⁩]*בתאריך\s`)
- Lines starting with `>` as fallback

### Required Environment Variables
```
TELEGRAM_BOT_TOKEN=
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
EMAIL_USERNAME=               # mailbox the bot acts as (e.g. bot@example.com)
SECRETARIAT_EMAIL=            # secretary's inbox
REDIS_URL=redis://localhost:6379/0
EMAIL_POLL_INTERVAL=30
LOG_LEVEL=INFO

# WhatsApp Business Cloud API — all three must be set to activate the adapter.
# When present, deploy.ps1 also enables external HTTPS ingress on port 8080.
WHATSAPP_TOKEN=                # Permanent access token from Meta
WHATSAPP_PHONE_NUMBER_ID=      # Phone-number ID for the production WhatsApp number (NOT the test number's ID)
WHATSAPP_VERIFY_TOKEN=         # Any random string; must match what's pasted into Meta's webhook config
```

### Azure Deployment (Production) ✅

The bot runs 24/7 on **Azure Container Apps** (North Europe). Redis runs as a sidecar container inside the same pod (`localhost:6379`) — no managed Redis service needed.

| Resource | Name | Notes |
| :--- | :--- | :--- |
| Resource Group | `rg-cpa-bot` | `israelcentral` |
| Container Registry | `remcpabotacr` | `israelcentral` |
| Container Apps Env | `cae-cpa-bot` | `northeurope` (Container Apps not available in israelcentral) |
| Container App | `ca-cpa-bot` | Bot + Redis sidecar; external HTTPS ingress on port 8080 |
| Public FQDN | shown by `deploy.ps1` after deploy | WhatsApp webhook is at `/webhook/whatsapp` on this FQDN |
| Telegram bot | configured via `TELEGRAM_BOT_TOKEN` in `.env` | Token from @BotFather |
| WhatsApp number | configured via `WHATSAPP_PHONE_NUMBER_ID` in `.env` | Registered under the WhatsApp Business Account in Meta |

**To redeploy after a code change:**
```powershell
# deploy.ps1 tags the image with the current git short SHA so Azure can't
# reuse a cached :latest. Commit your changes first, then:
$tag = (git rev-parse --short HEAD)
docker build -t remcpabotacr.azurecr.io/cpa-bot:$tag -t remcpabotacr.azurecr.io/cpa-bot:latest .
docker push remcpabotacr.azurecr.io/cpa-bot:$tag
docker push remcpabotacr.azurecr.io/cpa-bot:latest
powershell -ExecutionPolicy Bypass -File .\deploy.ps1
```

**To apply an env/secret change without rebuilding the image:**
```powershell
# Update .env, then re-run deploy.ps1 — it just updates secrets/config.
powershell -ExecutionPolicy Bypass -File .\deploy.ps1
# Container Apps may not auto-restart when only secret values change;
# force the running revision to pick them up:
az containerapp revision restart -n ca-cpa-bot -g rg-cpa-bot --revision <revision-name>
```

**To view live logs:**
```
az containerapp logs show -n ca-cpa-bot -g rg-cpa-bot --tail 50
```

**To tear down everything:**
```
az group delete --name rg-cpa-bot --yes
```

### Running locally
```bash
# Start Redis (WSL) — must use --bind 0.0.0.0 so Windows can reach it
wsl -u root -e bash -c "systemctl stop redis-server; redis-server --daemonize yes --bind 0.0.0.0 --protected-mode no"

# Set REDIS_URL to WSL IP (check with: wsl hostname -I)
# REDIS_URL=redis://172.29.180.1:6379/0

# Start bot
python -m src.main
```

**Common issues:**
- `ConnectionRefusedError` on Redis: WSL Redis bound to 127.0.0.1 — must stop systemd service first, then restart with `--bind 0.0.0.0`
- `Telegram 409 Conflict`: another bot instance still running — kill with `Get-Process python* | Stop-Process -Force`; if Azure deployment is running, stop local bot entirely

### Remaining MVP Features (not yet built)
* **Client Authentication:** Identify client by phone number via `ClientRepository.get_by_phone()` (currently using the pilot dict in `pilot_clients.py` as a stop-gap)
* **Self-Service File Retrieval:** Auto-fetch and send files to authenticated clients (option 2 bypass)
* **Automated Document Routing:** Route uploaded docs directly to the client's assigned accountant
* **Replace pilot dict with real client identification:** The 5-name dict in `src/repositories/pilot_clients.py` is a manual scaffold — swap for phone-based lookup once `ClientRepository` is populated

### Key Extension Points Already in Place
* `PlatformAdapter` ABC in `src/adapters/base.py` — both Telegram and WhatsApp implementations live
* `ClientRepository.get_by_phone()` exists and is ready for phone-number auth
* `UserSession` already has `client_id`, `client_name`, `phone` fields
* `MenuResponse(text, buttons=…)` gives a platform-agnostic return type — any new adapter just needs to render the buttons natively
* Redis session store is already persistent across restarts

---

## 4. Phase 3: Next Stage (AI Integration)
The final stage upgrades the bot from a simple menu-routing system to an intelligent conversational agent.

### New Features & Automations
* **LLM Integration:** An advanced Large Language Model (LLM) will handle free-text client inputs.
* **Conversational Capabilities:** The bot will autonomously continue correspondence, answer queries, and guide clients without requiring immediate human intervention.

### Key Extension Point
* Add option ד back to the menu and wire it to an LLM call in `menu_handler.py`. The FSM is designed to accommodate this without restructuring.

---

## 5. Key Stakeholders & Roles

| Stakeholder | Role & Interaction |
| :--- | :--- |
| **Clients** | End-users interacting with the bot via Telegram or WhatsApp to submit documents, request files, or ask questions. |
| **Secretariat (Admin)** | The frontline office workers who manage client requests via email. Their workload will decrease in later phases. |
| **Personal Accountants** | The CPAs who process bills/invoices and handle complex client messages. In the MVP stage, they will receive documents directly from the bot. |
