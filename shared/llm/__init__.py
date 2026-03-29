"""LLM integration module — model-agnostic client and narrative generation."""

from .client import LLMClient
from .narrative import NarrativeGenerator

__all__ = ["LLMClient", "NarrativeGenerator"]
