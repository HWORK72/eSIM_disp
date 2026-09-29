🇷🇺 [Читать на русском](README_RU.md)

An asynchronous Telegram dispatch engine engineered for inventory management, distribution workflows, and P2P fulfillment of digital eSIM profiles with crypto billing capabilities.

### Key Architectural Highlights:
* **Automated Inventory Lifecycle:** Secure ingestion, parsing, and structured storage of carrier QR profiles and IMSI payloads.
* **Queue & Hold Dispatcher:** Concurrency-safe reservation pipelines for instant wholesale lot acquisition in private dealer groups.
* **Financial Settlements:** Transaction request dispatching linked with Telegram CryptoBot payment references.
* **Role-Based Access Control (RBAC):** Distinct state machines and command handlers for system operators, bulk suppliers, and buyers.

### Tech Stack:
* Python 3.12
* Aiogram 3.x (Event-driven asynchronous Telegram framework)
* SQLite / SQLAlchemy (Transactional persistence layer)
* python-dotenv (Twelve-Factor configuration management)

### Quick Start:
```bash
pip install -r requirements.txt
python main.py
