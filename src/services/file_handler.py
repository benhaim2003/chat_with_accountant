from __future__ import annotations
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_UPLOAD_DIR = Path(tempfile.gettempdir()) / "cpa_bot_uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)


class FileHandler:
    def save_bytes(self, data: bytes, filename: str) -> str:
        dest = _UPLOAD_DIR / filename
        dest.write_bytes(data)
        logger.debug("Saved upload: %s", dest)
        return str(dest)

    def cleanup(self, file_path: str) -> None:
        try:
            os.remove(file_path)
            logger.debug("Cleaned up: %s", file_path)
        except OSError:
            pass
