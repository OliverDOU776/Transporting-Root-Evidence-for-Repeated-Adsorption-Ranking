"""Root evidence transport for repeated finite-support binary IAST ranking."""
from .engine import IASTEngine
from .stream import StreamRanker
from .data import load_corpus

__version__ = "0.1.0"
__all__ = ["IASTEngine", "StreamRanker", "load_corpus"]
