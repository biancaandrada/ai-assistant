"""Wipe the Chroma collection. Useful when changing embedding model or schema.

Usage:
    python -m scripts.reset_chroma             # asks for confirmation
    python -m scripts.reset_chroma --yes       # skip confirmation
"""
import sys

from app.clients import ChromaClient
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings)

    if "--yes" not in sys.argv:
        confirm = input(
            f"Reset collection '{settings.chroma_collection}' at "
            f"'{settings.chroma_path}'? [y/N] "
        )
        if confirm.strip().lower() != "y":
            print("aborted")
            return

    client = ChromaClient(settings)
    client.reset_collection(settings.chroma_collection)
    logger.info(f"collection '{settings.chroma_collection}' reset")


if __name__ == "__main__":
    main()
