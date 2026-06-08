from __future__ import annotations
import logging
import os

from app.classification.factory import get_classifier
from app.classification.mock_classifier import MockClassifier
from app.classification.model_config import get_active_model

logger = logging.getLogger(__name__)

_classifier = None


def _build() :
    model = get_active_model()
    if os.environ.get(model.api_key_env, ""):
        logger.info("Classifier: using AnthropicClassifier (%s)", model.model_id)
        return get_classifier()
    logger.warning(
        "Classifier: %s not set — falling back to MockClassifier (filename-based)",
        model.api_key_env,
    )
    return MockClassifier()


def classify_document(file_path: str) -> str:
    global _classifier
    if _classifier is None:
        _classifier = _build()
    return _classifier.classify(file_path)
