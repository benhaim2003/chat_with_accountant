# Project Context: Chat with Accountant

## 1. Project Overview
"Chat with Accountant" is an automated messaging and file-handling system designed for a Certified Public Accountant (CPA) office. The ultimate goal of the project is to:
* Streamline how the office handles routine client requests.
* Reduce the administrative burden on the secretariat.
* Improve client response times through an easy-to-use chat interface.

The project is structured into three distinct development phases: **Proof of Concept (POC)** ✅, **Minimum Viable Product (MVP)**, and **Next Stage (AI Integration)**.

### Architectural Philosophy: Forward Compatibility
A core requirement of this project is zero technical debt. The transition between phases must be a seamless evolution, not a complete rewrite. The codebase must be modular from day one—specifically anticipating the future addition of new platforms (WhatsApp), database-driven authentication, and LLM endpoints.

---

## 2. Phase 1: Proof of Concept (POC) — COMPLETE ✅

### What was built
A working Telegram bot that bridges client messages to the CPA office email system and routes secretary replies back to the client.

### Tech Stack
| Component | Technology |
| :--- | :--- |
| Messaging platform | Telegram (`python-telegram-bot>=22.0`) |
| Email | Microsoft Graph API (app-only auth via MSAL) |
| Session & thread storage | Redis (`redis>=5.0.0`) |
| Runtime | Python 3.12+ |

### Codebase Structure
```
src/
  adapters/
    base.py                  # PlatformAdapter ABC — add WhatsApp here in MVP
    telegram_adapter.py      # Telegram bot; thread-safe send via run_coroutine_threadsafe
    whatsapp_adapter.py      # Stub for MVP
  core/
    menu_handler.py          # FSM: routes messages through 8 states
    message_router.py        # Dispatches InternalMessage to MenuHandler
    session_manager.py       # Redis-backed session store (key: session:{platform}:{chat_id})
  infrastructure/
    redis_client.py          # Singleton get_redis() — reads REDIS_URL from env
  models/
    internal_message.py      # InternalMessage + Platform/MessageType enums
    user_model.py            # UserSession dataclass (persisted to Redis as JSON)
    client.py                # Client + Contact dataclasses
  repositories/
    client_repository.py     # Loads clients from data/clients.json (MVP: replace with DB)
  services/
    email_gateway.py         # GraphEmailGateway — send/poll via Microsoft Graph
    file_handler.py          # Saves incoming Telegram files to temp dir
  main.py                    # Wires everything together; on_secretary_reply callback
```

### Session State Machine
| State | Meaning |
| :--- | :--- |
| `idle` | No active session — next message shows the menu |
| `awaiting_option` | Menu shown, waiting for א/ב/ג/ד |
| `awaiting_file_upload` | Waiting for client to upload a document |
| `awaiting_file_request` | Waiting for client to describe which file they need |
| `awaiting_accountant_message` | Waiting for client's message to the accountant |
| `awaiting_other` | Waiting for client's free-text inquiry |
| `awaiting_session_decision` | Secretary replied; client prompted to close (1) or continue (2) |
| `session_open` | Active thread — client can send follow-ups |

### Redis Key Conventions
| Key | Value | TTL |
| :--- | :--- | :--- |
| `session:{platform}:{chat_id}` | JSON-serialized `UserSession` | 24 h (reset on every write) |
| `thread:{conversationId}` | `chat_id` (plain string) | 7 days |

### Email Bridge
1. Client sends a menu choice → `GraphEmailGateway.send()` creates a draft, sends it, stores `thread:{conversationId} → chat_id` in Redis.
2. Poller (every 30 s) reads unread messages in the mailbox, matches `conversationId` to a `chat_id` via Redis, strips quoted history and our own footer, detects `#close` marker.
3. Reply forwarded to client via Telegram. If `#close` was present, session moves to `awaiting_session_decision`.

### Required Environment Variables
```
TELEGRAM_BOT_TOKEN=
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
EMAIL_USERNAME=          # mailbox the bot acts as
SECRETARIAT_EMAIL=       # secretary's inbox
REDIS_URL=redis://localhost:6379/0
EMAIL_POLL_INTERVAL=30
LOG_LEVEL=INFO
```

### Running locally
```bash
# Start Redis (WSL)
wsl -u root -e bash -c "redis-server --daemonize yes --bind 0.0.0.0 --protected-mode no"

# Start bot
python -m src.main
```

---

## 3. Phase 2: Minimum Viable Product (MVP)
The MVP builds upon the POC by introducing a new communication channel, user authentication, and basic automation to reduce the secretariat's workload.

* **Expanded Platforms:** Telegram and WhatsApp

### New Features & Automations
* **Client Authentication:** The system will identify and verify the client based on their phone number.
* **Self-Service File Retrieval:** By leveraging phone number authentication, the bot will automatically locate and send requested files back to the client without requiring the secretary's intervention.
* **Automated Document Routing:** When an authenticated client uploads files (like bills or invoices), the bot will automatically identify the client and forward those specific documents directly to their assigned personal accountant, bypassing the general secretariat inbox.

### Key Extension Points Already in Place
* `PlatformAdapter` ABC in `src/adapters/base.py` — add `WhatsAppAdapter` without touching core logic.
* `ClientRepository.get_by_phone()` exists and is ready for phone-number auth.
* `UserSession` already has `client_id`, `client_name`, `phone` fields.
* Redis session store is already persistent across restarts — no rework needed.

---

## 4. Phase 3: Next Stage (AI Integration)
The final stage upgrades the bot from a simple menu-routing system to an intelligent conversational agent.

### New Features & Automations
* **LLM Integration:** An advanced Large Language Model (LLM) will be integrated to process the "Other" (free-text) inputs from the client.
* **Conversational Capabilities:** The bot will be able to read, understand, and extract intent from the client's free text. It will autonomously continue the correspondence with the client, answering queries or guiding them through processes without requiring immediate human intervention.

### Key Extension Point Already in Place
* `menu_handler._handle_other()` has a comment marking it as the Phase 3 hook — replace the email send with an LLM call there.

---

## 5. Key Stakeholders & Roles

| Stakeholder | Role & Interaction |
| :--- | :--- |
| **Clients** | End-users interacting with the bot via Telegram or WhatsApp to submit documents, request files, or ask questions. |
| **Secretariat (Admin)** | The frontline office workers who manage client requests via email. Their workload will decrease in later phases. |
| **Personal Accountants** | The CPAs who process bills/invoices and handle complex client messages. In the MVP stage, they will receive documents directly from the bot. |
