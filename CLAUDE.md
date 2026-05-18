# Accounting Document Reminder System - Project Guidelines

## Project Overview
This project is a lightweight, automated system built for an accounting firm. Its primary purpose is to cross-reference expected monthly client documents (e.g., utility bills, tax invoices) against actually received documents, identify missing files, and send automated reminders to clients.

## Architecture & Scope (MVP)
1. **Data Pipeline:** Read client configuration and expected document frequency.
2. **Core Engine:** Compare expected documents vs. dummy/local received files.
3. **Notification API:** Generate and send tailored reminder messages (e.g., via WhatsApp/SMS API).
4. **Modularity:** The system must be strictly modular. Data ingestion, logic, and external API calls must reside in separate modules.

## Tech Stack
- **Language:** Python 3.11+
- **Data Handling:** Native JSON/Dictionaries or `pandas` (only if data manipulation requires it).
- **Environment:** Virtual environment (`venv`), ready to be containerized (Docker) in the future.

## Strict Coding Guidelines
As an AI coding assistant, you must adhere strictly to the following rules:

1. **Type Hinting:** ALL functions and methods MUST include complete Python type hints (e.g., `def process_data(data: dict) -> list[str]:`).
2. **No Over-Engineering:** We are building an MVP. Do not add complex database setups (like PostgreSQL or SQLAlchemy) or heavy web frameworks (like Django) unless explicitly instructed. Stick to simple JSON/local files for now.
3. **Dependencies:** Do NOT install external libraries unless absolutely necessary. Ask for user confirmation before adding a new dependency to `requirements.txt`.
4. **Error Handling & Logging:** Use Python's built-in `logging` module instead of `print()`. Catch specific exceptions rather than using bare `except:`.
5. **Language:** Keep variables, functions, and documentation in English. 

## Project Structure (Target)
├── main.py # Entry point
├── config.py # Environment variables and constants
├── data_manager.py # Logic for parsing expected vs. received documents
├── notifier.py # API integration for sending messages
├── dummy_files/ # Directory to mock Google Drive/received files
├── requirements.txt
└── CLAUDE.md # You are reading this file

## Execution Commands
- To run the main script: `python main.py`
- To test specific modules: `python -m unittest` or `pytest`