"""Claustor AI — Global Entity & Identifier Extraction Framework."""
from .engine import get_identifier_engine, ExtractionResult, IdentifierMatch
from .registry import IdentifierRegistry

__all__ = [
    "get_identifier_engine",
    "ExtractionResult",
    "IdentifierMatch",
    "IdentifierRegistry",
]
