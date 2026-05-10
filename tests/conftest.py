"""
conftest.py — stubs out heavy GPU/ML dependencies so the test suite can
run on any machine (CI, macOS dev box, etc.) without a CUDA GPU.
"""
import sys
from unittest.mock import MagicMock

# Modules that require a physical CUDA GPU / large model weights
_HEAVY_MODULES = [
    "torch",
    "diffusers",
    "diffusers.pipelines",
    "transformers",
    "accelerate",
    "nvidia",
    "nvimgcodec",
    "aiohttp",
]

for _mod in _HEAVY_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
