"""TERN STAC convenience library."""

from ._version import __version__
from .client import TernStacClient, load_from_tern

__all__ = ["TernStacClient", "load_from_tern", "__version__"]
