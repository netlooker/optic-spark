"""
conftest.py — stubs out heavy GPU/ML dependencies so the test suite can
run on any machine (CI, macOS dev box, etc.) without a CUDA GPU.
"""
import os
import sys
from unittest.mock import MagicMock

# Ensure OUTPUT_DIR is set before src.main is imported (avoids /app mkdir on non-container hosts)
if "OUTPUT_DIR" not in os.environ:
    os.environ["OUTPUT_DIR"] = "/tmp/optic-spark-test-output"

# Modules that require a physical CUDA GPU / large model weights
_HEAVY_MODULES = [
    "torch",
    "diffusers",
    "diffusers.pipelines",
    "transformers",
    "accelerate",
    "aiohttp",
]

for _mod in _HEAVY_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
