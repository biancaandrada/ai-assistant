"""Thin SDK wrapper around ChromaDB. Manages the persistent client & collection."""
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..core.config import Settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChromaClient:
    def __init__(self, settings: Settings) -> None:
        self._client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection
        )
        logger.info(
            f"ChromaClient ready: path={settings.chroma_path} "
            f"collection={settings.chroma_collection}"
        )

    @property
    def collection(self):
        return self._collection

    def reset_collection(self, name: str) -> None:
        try:
            self._client.delete_collection(name=name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(name=name)
