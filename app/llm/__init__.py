"""Adapters for approved, local language-model services only."""

from .ollama_client import LocalServiceUnavailable, OllamaClient

__all__ = ["LocalServiceUnavailable", "OllamaClient"]

