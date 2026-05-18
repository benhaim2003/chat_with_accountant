import dataclasses
import pytest
from unittest.mock import patch

from app.classification.model_config import (
    AVAILABLE_MODELS,
    get_active_model,
    ModelConfig,
)


class TestAvailableModels:
    def test_contains_anthropic_models(self) -> None:
        anthropic_keys = [k for k, v in AVAILABLE_MODELS.items() if v.provider == "anthropic"]
        assert len(anthropic_keys) >= 1

    def test_contains_openai_models(self) -> None:
        openai_keys = [k for k, v in AVAILABLE_MODELS.items() if v.provider == "openai"]
        assert len(openai_keys) >= 1

    def test_contains_gemini_models(self) -> None:
        gemini_keys = [k for k, v in AVAILABLE_MODELS.items() if v.provider == "gemini"]
        assert len(gemini_keys) >= 1

    def test_all_entries_have_api_key_env(self) -> None:
        for key, model in AVAILABLE_MODELS.items():
            assert model.api_key_env, f"{key} is missing api_key_env"

    def test_model_config_is_immutable(self) -> None:
        model = AVAILABLE_MODELS["claude-sonnet-4-6"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            model.provider = "other"  # type: ignore[misc]


class TestGetActiveModel:
    def test_returns_default_model(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import app.classification.model_config as mc
            original = mc.ACTIVE_MODEL_KEY
            # patch the module-level constant
            mc.ACTIVE_MODEL_KEY = "claude-sonnet-4-6"
            model = get_active_model()
            assert model.provider == "anthropic"
            assert "sonnet" in model.model_id
            mc.ACTIVE_MODEL_KEY = original

    def test_invalid_key_raises_value_error(self) -> None:
        import app.classification.model_config as mc
        original = mc.ACTIVE_MODEL_KEY
        mc.ACTIVE_MODEL_KEY = "totally-unknown-model"
        with pytest.raises(ValueError, match="Unknown model"):
            get_active_model()
        mc.ACTIVE_MODEL_KEY = original

    def test_error_message_lists_available_keys(self) -> None:
        import app.classification.model_config as mc
        original = mc.ACTIVE_MODEL_KEY
        mc.ACTIVE_MODEL_KEY = "bad-key"
        with pytest.raises(ValueError) as exc_info:
            get_active_model()
        for key in AVAILABLE_MODELS:
            assert key in str(exc_info.value)
        mc.ACTIVE_MODEL_KEY = original
