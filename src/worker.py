import logging
import aiohttp
import os
import re
import asyncio
from datetime import datetime
from uuid import UUID
from .schemas import GenerateImageRequest, WebhookDeliveryPayload
from .engine import generate

logger = logging.getLogger("optic-spark.worker")

# Prevent concurrent GPU executions to avoid CUDA OOM crashes
gpu_lock = asyncio.Lock()

def generate_filename(prompt: str, job_id: UUID, ext: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r'[^a-z0-9\s]', '', prompt.lower()).split()[:5]
    slug_str = "_".join(slug)
    short_id = str(job_id)[:8]
    return f"{timestamp}_{slug_str}_{short_id}.{ext}"

async def process_image_generation(job_id: UUID, request: GenerateImageRequest):
    logger.info(f"⚙️  [PIPELINE STARTED] Job: {job_id}")
    
    try:
        # Run synchronous generation in a threadpool to prevent blocking the FastAPI event loop
        # We wrap this in an asyncio.Lock to ensure only ONE generation happens at a time to prevent CUDA OOM
        logger.info(f"⏳ Job: {job_id} waiting for GPU lock...")
        async with gpu_lock:
            logger.info(f"⚡ Job: {job_id} acquired GPU lock! Generating...")
            image_bytes = await asyncio.to_thread(
                generate,
                prompt=request.prompt,
                aspect_ratio=request.aspect_ratio,
                output_format=request.output_format
            )
        
        # Save to local output directory with meaningful filename
        filename = generate_filename(request.prompt, job_id, request.output_format)
        output_dir = os.environ.get("OUTPUT_DIR", "/app/output")
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
            
        logger.info(f"✅ [GENERATION COMPLETE] Job: {job_id} | Saved to: {filename}")
            
        # The URL now points to the static file server
        base_url = os.environ.get("BASE_URL", "http://localhost:7070")
        image_url = f"{base_url.rstrip('/')}/output/{filename}"
        
        payload = WebhookDeliveryPayload(
            job_id=job_id,
            status="completed",
            image_url=image_url
        )
        
    except FileNotFoundError as e:
        logger.error(f"❌ [MODEL NOT FOUND] Job: {job_id} | {e}")
        payload = WebhookDeliveryPayload(
            job_id=job_id,
            status="failed",
            error_code="MODEL_NOT_FOUND",
            error_hint=str(e)
        )
    except Exception as e:
        logger.error(f"❌ [PIPELINE FAILED] Job: {job_id} | {type(e).__name__}: {e}")
        payload = WebhookDeliveryPayload(
            job_id=job_id,
            status="failed",
            error_code="INFERENCE_ERROR",
            error_hint=str(e)
        )
        
    # Deliver webhook
    logger.info(f"📡 [DISPATCHING WEBHOOK] Job: {job_id} | Target: {request.webhook_url}")
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(str(request.webhook_url), json=payload.model_dump(mode="json")) as response:
                logger.info(f"🎉 [WEBHOOK DELIVERED] Job: {job_id} | HTTP Status: {response.status}")
        except Exception as e:
            logger.error(f"❌ [WEBHOOK FAILED] Job: {job_id} | Error: {e}")
