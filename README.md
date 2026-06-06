# Doctor's Assistant - AI Chatbot for Appointment Scheduling

A learning project implementing an AI-powered chatbot that helps patients book doctor appointments using natural language conversations. Built with Python, OpenAI's Responses API with Tool Calling, and an in-memory SQLite database.

## Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API key

### Setup
```bash
cd doctor_assistant
pip install -r requirements.txt

# Copy and configure your API key
cp .env.example .env
# Edit .env and add your OpenAI API key: OPENAI_API_KEY=sk-...
```

### Run
```bash
# Interactive mode (chat with the bot)
python -m doctor_assistant.main

# Demo mode (runs all 3 predefined scenarios automatically)
python -m doctor_assistant.main --demo
```

---

## Design & Architecture (Learning Guide)

### 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     doctor_assistant/                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  main.py (Orchestrator)                                  │    │
│  │  - CLI interface (interactive + demo modes)              │    │
│  │  - Manages conversation lifecycle                        │    │
│  └──────────┬──────────┬──────────┬────────────────────────┘    │
│             │          │          │                              │
│      ┌──────▼──┐ ┌─────▼─────┐ ┌─▼───────────────┐              │
│      │ config/ │ │   db/     │ │     llm/         │              │
│      │settings │ │  models   │ │ openai_client    │              │
│      │ .env    │ │ SQLite    │ │ + tool calling   │              │
│      └─────────┘ └─────┬─────┘ └─▲───────────────┘              │
│                        │         │                               │
│                  ┌─────▼─────────┴──┐                            │
│                  │   tools/         │                             │
│                  │  definitions.py │                             │
│                  │  handlers       │                             │
│                  └─────────────────┘                             │
└──────────────────────────────────────────────────────────────────┘

          Layer             Responsibility              Dependencies
  ────────────────────  ────────────────────  ─────────────────────────
  Presentation         CLI interface (main)   Application Layer
  Application          LLM orchestration      Domain Layer + Config
  Domain               Tool definitions       Persistence Layer
  Persistence          Database operations     Python's sqlite3
  Configuration        Settings management    Environment + .env
```

### 2. Configuration-Driven LLM Integration

**What is it?**
Instead of hardcoding which AI model to use or where the API key comes from, we use configuration files (`.env`) to specify these at runtime.

**Why is this important?**
- **Swap models without code changes**: Change `OPENAI_MODEL=gpt-4o-mini` to `OPENAI_MODEL=gpt-4o` in `.env` — no code modifications needed.
- **Switch providers**: Add a `LLM_PROVIDER=anthropic` setting and implement a different client class. The rest of the code stays the same.
- **Security**: API keys stay out of source code (never committed to git).
- **Environment isolation**: Different API keys for dev/test/prod.

**How it works:**
```python
# config/settings.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Load from environment
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # With default
```

### 3. In-Memory Database (SQLite vs MySQL)

**The Requirement**: "MySQL InMemory DB"

**The Reality**: We use **SQLite with `:memory:` mode**. Here's why:

| Aspect               | SQLite :memory:          | MySQL MEMORY Engine      |
|----------------------|--------------------------|--------------------------|
| Setup Required       | None (built into Python) | MySQL server installation |
| Truly In-Memory      | ✅ Yes                   | ✅ Yes                    |
| SQL Support          | ✅ Full SQL              | ✅ Full SQL               |
| Learning Value       | ✅ High (real SQL)       | ✅ High                   |
| Production Ready     | ❌ (not for multi-user)  | ✅ (with clustering)     |
| Persistence Option   | File-based possible      | Disk by default           |

**Key learning**: The database schema, SQL queries, and repository pattern would be **identical** with MySQL. Only the connection string changes (`:memory:` → `mysql://...`).

### 4. Database Schema (3rd Normal Form)

```
┌──────────────┐     ┌────────────────┐     ┌──────────────────┐
│  departments │     │    doctors     │     │  availabilities  │
├──────────────┤     ├────────────────┤     ├──────────────────┤
│  id (PK)     │◄────│  department_id │     │  id (PK)         │
│  name        │     │  id (PK)       │◄────│  doctor_id       │
│  description │     │  name          │     │  day_of_week     │
└──────────────┘     │  phone         │     │  start_time      │
                     │  email         │     │  end_time        │
                     └────────────────┘     └──────────────────┘
                            │
                            │
                     ┌──────▼───────┐     ┌──────────────────┐
                     │ appointments │     │    patients      │
                     ├──────────────┤     ├──────────────────┤
                     │  id (PK)     │     │  id (PK)         │
                     │  doctor_id   │     │  name            │
                     │  patient_id  │────►│  phone           │
                     │  date        │     │  email           │
                     │  start_time  │     └──────────────────┘
                     │  end_time    │
                     │  reason      │
                     │  created_at  │
                     └──────────────┘
```

**Normalization**: Data is organized to eliminate redundancy:
- Doctor info stored once, referenced by ID
- Department info stored once, referenced by ID
- Patient info stored once, referenced by ID
- Appointments link doctors, patients, and time slots

### 5. OpenAI Tool/Function Calling Pattern

This is the **core design pattern** that makes the chatbot intelligent.

**The Problem**: LLMs can understand language but can't directly query databases.

**The Solution**: Tool Calling bridges this gap:

```
User: "I'd like to see Dr. Sharma tomorrow at 10 AM"
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  1. Send to OpenAI with tools defined       │
│                                             │
│  Available tools:                           │
│    - get_doctor_by_name(name)               │
│    - get_available_slots(doctor_id, date)   │
│    - book_appointment(...)                  │
│    - get_departments()                      │
│    - suggest_alternative_doctor(...)        │
│    - get_today_date()                       │
│    - get_all_doctors()                      │
│    - get_doctors_by_department(name)        │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  2. OpenAI decides to call:                 │
│     get_doctor_by_name("Dr. Sharma")        │
│     Returns: {id: 1, name: "Dr. Sharma"}    │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  3. OpenAI calls:                           │
│     get_today_date()                        │
│     Returns: "2026-06-06 (Saturday)"        │
│     Decides: tomorrow = 2026-06-08 (Monday) │
│     Calls: get_available_slots(1, "2026-06-08") │
│     Returns: ["09:00", "09:30", ...]        │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  4. OpenAI responds to user:                │
│     "Dr. Sharma is available tomorrow.      │
│      He has slots at 9:00 AM, 9:30 AM...   │
│      Would you like to book one?"          │
└─────────────────────────────────────────────┘
```

**The Loop**:
1. Send user message + conversation history + tool definitions to OpenAI
2. OpenAI either responds OR requests a tool call
3. If tool call: execute our Python function, send result back, GOTO step 2
4. If response: display to user, wait for next input

**Safety**: Maximum 15 iterations to prevent infinite loops.

### 6. Code Organization & Patterns

#### Repository Pattern (db/models.py)
```python
class DoctorAssistantDB:
    """All database operations go through this class."""
    
    def get_available_slots(self, doctor_id, date): ...
    def book_appointment(self, ...): ...
    def get_doctors_by_department(self, name): ...
```

**Why?** If we switch from SQLite to MySQL, only this file changes.

#### Handler Pattern (tools/tools_definitions.py)
```python
# Each tool maps to a handler function
handlers = {
    "get_doctor_by_name": handle_get_doctor_by_name,
    "get_available_slots": handle_get_available_slots,
    "book_appointment": handle_book_appointment,
    # ...
}
```

**Why?** Clean separation between "tool definitions for OpenAI" and "actual implementation."

#### Conversation Loop (llm/openai_client.py)
```python
class OpenAIChatClient:
    def get_response(self):
        while iteration < max_iterations:
            response = openai.chat.completions.create(
                messages=self.messages,
                tools=self.tools
            )
            if response.has_tool_calls:
                execute_tool(response.tool_calls)
                # Append result as "tool" message
                continue
            return response.text
```

### 7. Sample Data

| Doctor | Department | Availability |
|--------|-----------|-------------|
| Dr. Sharma | Cardiology | Mon-Fri 9am-5pm |
| Dr. Patel | Dermatology | Mon, Wed, Fri 10am-4pm |
| Dr. Singh | Orthopedics | Tue-Thu 8am-2pm, Sat 9am-1pm |
| Dr. Gupta | Orthopedics | Mon-Fri 11am-7pm |
| Dr. Verma | Pediatrics | Mon-Sat 9am-3pm |
| Dr. Joshi | Neurology | Mon, Wed, Fri 10am-4pm |
| Dr. Desai | Cardiology | Tue, Thu 2pm-8pm |
| Dr. Kapoor | General Medicine | Mon-Sat 9am-5pm |

### 8. Conversation Scenarios

The demo mode (`--demo`) runs three scenarios:

**Scenario 1**: Direct doctor request → time negotiation → booking
**Scenario 2**: Symptom description → no specialist available → polite decline
**Scenario 3**: Symptom description → specialist found → alternative doctor → booking

Each demonstrates different aspects of the tool-calling loop.

---

## Key Learning Concepts

1. **Tool-Augmented LLMs**: How LLMs use external tools to overcome their limitations (no direct database access).

2. **Configuration-Driven Design**: Keeping credentials and model choices in configuration, not code.

3. **Repository Pattern**: Abstracting database operations behind an interface.

4. **In-Memory Databases**: Understanding the tradeoffs between SQLite :memory: and MySQL MEMORY engine.

5. **Conversation State Management**: How message history + tool results maintain coherent multi-turn conversations.

6. **Slot-Based Scheduling**: Checking availability by subtracting booked slots from available slots.

7. **3rd Normal Form (3NF)**: Why splitting data across multiple tables reduces redundancy.

8. **API Architecture**: The layered architecture (Presentation → Application → Domain → Persistence → Configuration).

---

## File Structure

```
doctor_assistant/
├── main.py                      # Entry point, CLI interface
├── requirements.txt              # Dependencies
├── .env.example                  # Configuration template
├── README.md                     # This file
├── config/
│   ├── __init__.py
│   └── settings.py              # Environment configuration
├── db/
│   ├── __init__.py
│   └── models.py                # Database schema + operations
├── llm/
│   ├── __init__.py
│   └── openai_client.py         # OpenAI API client with tool calling
└── tools/
    ├── __init__.py
    └── tools_definitions.py     # Tool definitions + handlers
```

## Future Enhancements

1. **Multiple LLM Providers**: Add support for Anthropic Claude, Google Gemini, or local models (Ollama).
2. **Persistent Database**: Switch from SQLite :memory: to PostgreSQL/MySQL for production use.
3. **Web Interface**: Build a FastAPI/Flask web server instead of CLI.
4. **Authentication**: Add user authentication for patients.
5. **Email/SMS Notifications**: Send appointment confirmations.
6. **Advanced Scheduling**: Handle recurring appointments, multi-day searches, etc.
7. **Conversation Memory**: Store conversation history for analysis and training.