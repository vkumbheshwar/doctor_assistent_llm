"""
Configuration Module
====================
Loads configuration from environment variables with sensible defaults.

DESIGN CONCEPT: Configuration-Driven LLM Integration
------------------------------------------------------
Instead of hardcoding an LLM provider or API key, we use a configuration
file (`.env`) to specify:
  - Which LLM provider/model to use
  - API keys / credentials
  - Other adjustable parameters (temperature, max tokens)

This approach is called "Configuration-Driven Design" and allows:
  1. Switching between LLM providers without code changes
  2. Using different models (GPT-4o, GPT-4o-mini, etc.)
  3. Keeping credentials out of source code (security best practice)
  4. Easy deployment across different environments (dev, test, prod)

ENVIRONMENT VARIABLES vs CONFIG FILES:
- Environment variables are better for secrets (API keys) since they're
  less likely to be committed to version control.
- A `.env` file bridges the gap - it's local-only and never committed.
- `python-dotenv` loads `.env` into `os.environ` at startup.

Future Enhancement:
  To support multiple LLM providers (e.g., Anthropic, Google, local models),
  add a LLM_PROVIDER variable and create provider-specific client classes.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Build path to .env file (same directory as this settings.py, i.e., config/)
ENV_PATH = Path(__file__).parent.parent / ".env"

# Load .env if it exists
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"  [Config] Loaded settings from: {ENV_PATH}")
else:
    print(
        "  [Config] No .env file found. "
        "Using environment variables or defaults. "
        f"Create {ENV_PATH} from .env.example to customize."
    )


# --- OpenAI / LLM Settings ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY is not set. "
        "Either set it as an environment variable or create a .env file "
        "in the project root based on .env.example"
    )

OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

# --- Clinic Settings ---
CLINIC_NAME: str = os.getenv("CLINIC_NAME", "Super Clinic")

# --- System Prompt ---
# This is the "personality" and instruction set for the AI assistant.
# The system prompt defines:
#   - The assistant's role (Doctor's Appointment Assistant)
#   - Behavioral guidelines (be polite, don't guess availability)
#   - The tool-calling boundary (when to look up or modify DB)
SYSTEM_PROMPT: str = (
    "You are a helpful and friendly appointment scheduling assistant "
    f"for '{CLINIC_NAME}'. "
    "Your role is to help patients book appointments with doctors "
    "based on their symptoms or direct requests.\n\n"
    "Guidelines:\n"
    "1. Greet the patient warmly when they call.\n"
    "2. If the caller describes symptoms, determine the appropriate "
    "specialty/department and look up matching doctors using the tools.\n"
    "3. If the caller directly asks for a doctor by name, look them up.\n"
    "4. Check doctor availability before suggesting appointments.\n"
    "5. If a doctor is unavailable, suggest alternatives (different time "
    "or different doctor).\n"
    "6. When booking, collect the patient's name and optionally phone.\n"
    "7. Be empathetic - patients may be anxious about their health.\n"
    "8. NEVER invent or hallucinate doctor availability. Always use the "
    "provided tools to check.\n"
    "9. If no suitable doctor/specialty is available, inform the patient "
    "politely and offer to help with anything else.\n"
    "10. Keep responses concise and conversational, not robotic."
)