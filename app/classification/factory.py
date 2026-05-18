import os

from app.classification.base import DocumentClassifier
from app.classification.anthropic_classifier import AnthropicClassifier
from app.classification.model_config import get_active_model


def get_classifier() -> DocumentClassifier:
    model = get_active_model()

    api_key = os.environ.get(model.api_key_env, "")
    if not api_key:
        raise EnvironmentError(
            f"API key not set. Add {model.api_key_env} to your .env file."
        )

    if model.provider == "anthropic":
        return AnthropicClassifier(model_id=model.model_id, api_key=api_key)

    raise NotImplementedError(
        f"Provider '{model.provider}' is not yet supported. "
        "Set ACTIVE_MODEL to a Claude model key (e.g. claude-sonnet-4-6)."
    )
