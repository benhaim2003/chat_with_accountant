import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    provider: str       # "anthropic" | "openai" | "gemini"
    model_id: str       # exact API model identifier
    display_name: str   # human-readable label
    api_key_env: str    # env var name that holds the API key


AVAILABLE_MODELS: dict[str, ModelConfig] = {
    # --- Anthropic / Claude ---
    "claude-opus-4-7": ModelConfig(
        provider="anthropic",
        model_id="claude-opus-4-7",
        display_name="Claude Opus 4.7 (Anthropic) — most capable",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-sonnet-4-6": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6 (Anthropic) — balanced speed/intelligence",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-haiku-4-5": ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5 (Anthropic) — fastest / cheapest",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    # --- OpenAI / GPT ---
    "gpt-4o": ModelConfig(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o (OpenAI) — most capable",
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-4o-mini": ModelConfig(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini (OpenAI) — fast / cheap",
        api_key_env="OPENAI_API_KEY",
    ),
    # --- Google / Gemini ---
    "gemini-2.0-flash": ModelConfig(
        provider="gemini",
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash (Google) — fast",
        api_key_env="GEMINI_API_KEY",
    ),
    "gemini-1.5-pro": ModelConfig(
        provider="gemini",
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro (Google) — capable",
        api_key_env="GEMINI_API_KEY",
    ),
}

# Set ACTIVE_MODEL env var to any key above to switch providers.
# Defaults to Claude Sonnet 4.6 — change the fallback string to your preference.
ACTIVE_MODEL_KEY: str = os.environ.get("ACTIVE_MODEL", "claude-sonnet-4-6")


def get_active_model() -> ModelConfig:
    if ACTIVE_MODEL_KEY not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS.keys())
        raise ValueError(
            f"Unknown model '{ACTIVE_MODEL_KEY}'. Available: {available}"
        )
    return AVAILABLE_MODELS[ACTIVE_MODEL_KEY]


def list_models() -> None:
    print("Available models (set ACTIVE_MODEL=<key> to select):\n")
    for key, model in AVAILABLE_MODELS.items():
        active = " ← active" if key == ACTIVE_MODEL_KEY else ""
        print(f"  {key:<22}  {model.display_name}{active}")
