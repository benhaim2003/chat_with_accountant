# Project Context: Chat with Accountant

## 1. Project Overview
"Chat with Accountant" is an automated messaging and file-handling system designed for a Certified Public Accountant (CPA) office. The ultimate goal of the project is to:
* Streamline how the office handles routine client requests.
* Reduce the administrative burden on the secretariat.
* Improve client response times through an easy-to-use chat interface.

The project is structured into three distinct development phases: **Proof of Concept (POC)**, **Minimum Viable Product (MVP)**, and **Next Stage (AI Integration)**.

### Architectural Philosophy: Forward Compatibility
A core requirement of this project is zero technical debt. The transition between phases must be a seamless evolution, not a complete rewrite. The codebase must be modular from day one—specifically anticipating the future addition of new platforms (WhatsApp), database-driven authentication, and LLM endpoints. 

---

## 2. Phase 1: Proof of Concept (POC)
The POC focuses on establishing a basic communication bridge between the client's chat app and the CPA office's email system.

* **Primary Platform:** Telegram

### Strict Constraint: No "POC Shortcuts"
While this phase is a proof of concept, "throwaway code" or hardcoded workarounds are strictly prohibited. The underlying message-handling architecture must be scalable and extensible so that moving to the MVP and Next Stage requires adding new modules rather than refactoring the core system.

### User Flow
1. The client initiates a conversation by sending a message to the bot.
2. The bot immediately responds with an automated menu featuring four default options:
    * **Option A:** Upload an invoice or bill of costs.
    * **Option B:** Request a specific file currently held by the CPA office.
    * **Option C:** Leave a message for their personal accountant.
    * **Option D:** Other (Allows the client to type a free-text message).

### Backend Workflow (The Email Bridge)
1. Once the client makes a selection or uploads a file, the bot generates an email containing the client's details and their specific request.
2. This email is sent directly to the office secretariat.
3. The secretary reviews the request and replies directly to the email.
4. The bot intercepts the secretary's email reply and forwards the text/files back to the client via Telegram.

---

## 3. Phase 2: Minimum Viable Product (MVP)
The MVP builds upon the POC by introducing a new communication channel, user authentication, and basic automation to reduce the secretariat's workload.

* **Expanded Platforms:** Telegram and WhatsApp

### New Features & Automations
* **Client Authentication:** The system will identify and verify the client based on their phone number.
* **Self-Service File Retrieval:** By leveraging phone number authentication, the bot will automatically locate and send requested files back to the client without requiring the secretary's intervention.
* **Automated Document Routing:** When an authenticated client uploads files (like bills or invoices), the bot will automatically identify the client and forward those specific documents directly to their assigned personal accountant, bypassing the general secretariat inbox.

---

## 4. Phase 3: Next Stage (AI Integration)
The final stage upgrades the bot from a simple menu-routing system to an intelligent conversational agent.

### New Features & Automations
* **LLM Integration:** An advanced Large Language Model (LLM) will be integrated to process the "Other" (free-text) inputs from the client.
* **Conversational Capabilities:** The bot will be able to read, understand, and extract intent from the client's free text. It will autonomously continue the correspondence with the client, answering queries or guiding them through processes without requiring immediate human intervention.

---

## 5. Key Stakeholders & Roles

| Stakeholder | Role & Interaction |
| :--- | :--- |
| **Clients** | End-users interacting with the bot via Telegram or WhatsApp to submit documents, request files, or ask questions. |
| **Secretariat (Admin)** | The frontline office workers who, in the POC stage, manage client requests via email. Their manual workload will decrease in later phases. |
| **Personal Accountants** | The CPAs who ultimately process the bills/invoices and handle complex client messages. In the MVP stage, they will receive documents directly from the bot. |