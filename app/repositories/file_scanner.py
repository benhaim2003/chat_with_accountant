from __future__ import annotations
import logging
from pathlib import Path

from app.classification.base import DocumentClassifier
from app.models.client import Client
from app.models.document import ClientReceivedDocs, ReceivedDocument

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".pdf"}


class FileScanner:
    """Scans a directory of client folders, classifies each file,
    and returns the results as ClientReceivedDocs objects."""

    def __init__(self, files_dir: str, classifier: DocumentClassifier) -> None:
        self._files_dir = Path(files_dir)
        self._classifier = classifier

    def build_received_docs(
        self, clients: list[Client], month: str
    ) -> list[ClientReceivedDocs]:
        result: list[ClientReceivedDocs] = []
        for client in clients:
            folder = self._find_client_folder(client.id)
            received: list[ReceivedDocument] = []

            if folder is None:
                logger.warning("No folder found for client %s (%s)", client.id, client.name)
            else:
                files = self._list_files(folder)
                logger.info(
                    "Scanning %s — %d file(s) found", folder.name, len(files)
                )
                for filepath in files:
                    doc_type = self._classifier.classify(str(filepath))
                    logger.info("  %-45s → %s", filepath.name, doc_type)
                    received.append(
                        ReceivedDocument(
                            type=doc_type,
                            filename=filepath.name,
                            received_at=f"{month}-01",
                        )
                    )

            result.append(
                ClientReceivedDocs(client_id=client.id, month=month, received=received)
            )
        return result

    def _find_client_folder(self, client_id: str) -> Path | None:
        if not self._files_dir.exists():
            logger.error("Files directory not found: %s", self._files_dir)
            return None
        for entry in self._files_dir.iterdir():
            if entry.is_dir() and entry.name.startswith(f"{client_id}_"):
                return entry
        return None

    def _list_files(self, folder: Path) -> list[Path]:
        return sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
        )
