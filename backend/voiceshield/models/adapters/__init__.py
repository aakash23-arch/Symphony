"""Concrete model adapters (C-20..C-25).

These are the ONLY modules in the codebase permitted to import torch or
transformers, and they do so lazily inside ``load()`` so that importing
``voiceshield.models`` works on a machine with no ML stack installed.

Everything above this package talks to the protocols in ``models/interfaces.py``
and never to an ML library directly. ``tests/test_architecture_boundaries.py``
enforces that separation.
"""

from .hf_wav2vec2_spoof import Wav2Vec2SpoofAdapter
from .hf_wavlm_xvector import WavLMXVectorAdapter

__all__ = ["Wav2Vec2SpoofAdapter", "WavLMXVectorAdapter"]
