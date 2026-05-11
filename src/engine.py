import io
import logging
import os
import threading

import torch
from diffusers import GGUFQuantizationConfig, ZImagePipeline
from diffusers.models import ZImageTransformer2DModel

logger = logging.getLogger("optic-spark.engine")

# The full pipeline repo on HF (text encoder, VAE, tokenizer, scheduler)
HF_MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"

# Constants
MODEL_PATH = os.environ.get("MODEL_PATH", "/model")
pipeline = None
_pipeline_lock = threading.Lock()


def get_gguf_file():
    # Allow exact path override if user specified in .env
    exact_path = os.environ.get("GGUF_MODEL_PATH")
    if exact_path and os.path.exists(exact_path):
        return exact_path

    # Otherwise auto-discover the model
    for root, _dirs, files in os.walk(MODEL_PATH):
        for file in files:
            if "Q4_K_M.gguf" in file:
                return os.path.join(root, file)
    return None


def get_pipeline():
    global pipeline
    # Fast path: already loaded
    if pipeline is not None:
        return pipeline

    # Slow path: acquire lock to prevent double-loading across threads
    with _pipeline_lock:
        if pipeline is not None:  # re-check inside lock
            return pipeline

        gguf_file = get_gguf_file()
        if not gguf_file:
            raise FileNotFoundError(f"No Q4_K_M GGUF model found in {MODEL_PATH}")

        logger.info(f"📦 [LOADING TRANSFORMER] GGUF from: {gguf_file}...")

        # Load only the transformer from the GGUF file (it does NOT contain
        # the text encoder, VAE, tokenizer or scheduler)
        quantization_config = GGUFQuantizationConfig(compute_dtype=torch.bfloat16)
        transformer = ZImageTransformer2DModel.from_single_file(
            gguf_file,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16,
        )

        logger.info(f"🔗 [PIPELINE ASSEMBLY] Loading auxiliary components from HF hub: {HF_MODEL_ID}...")

        # Load text encoder, VAE, tokenizer and scheduler from the full HF model.
        # The quantized transformer above is injected in place of the full one.
        pipeline = ZImagePipeline.from_pretrained(
            HF_MODEL_ID,
            transformer=transformer,
            torch_dtype=torch.bfloat16,
        ).to("cuda")

        return pipeline

def generate(prompt: str, aspect_ratio: str, output_format: str) -> bytes:
    pipe = get_pipeline()

    # Map aspect ratio to the most popular web/device resolutions
    ar_map = {
        "1:1": (1024, 1024),      # Standard GenAI / High-res Social Square
        "16:9": (1280, 720),      # HD 720p (YouTube standard)
        "9:16": (720, 1280),      # Mobile HD (TikTok, Shorts, Reels)
        "4:3": (1024, 768),       # XGA (Standard traditional monitor/tablet)
        "3:4": (768, 1024),       # Vertical XGA
        "3:2": (1200, 800),       # Standard WXGA (popular laptop/tablet)
        "2:3": (800, 1200),       # Standard WXGA vertical
    }
    width, height = ar_map.get(aspect_ratio, (1024, 1024))

    logger.info(f"🎨 [INFERENCE RUNNING] Hardware crunching size: {width}x{height}")

    # Generate image
    image = pipe(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=8,
        guidance_scale=0.0,
    ).images[0]

    # Encode output to bytes
    buffer = io.BytesIO()
    fmt_map = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
    image.save(buffer, format=fmt_map.get(output_format, "PNG"))
    return buffer.getvalue()
