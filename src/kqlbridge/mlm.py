"""
mlm.py — Backward-compatibility wrapper for TranslationMemory
==============================================================
This module preserves the legacy MLMAgent class name for backwards compatibility.
"""

from .memory import TranslationMemory

# Export MLMAgent as an alias to the new TranslationMemory
MLMAgent = TranslationMemory
