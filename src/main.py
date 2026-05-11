import asyncio
import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles

from .engine import get_pipeline
from .schemas import GenerateImageRequest, GenerateImageResponse
from .worker import process_image_generation

# Configure beautiful and structured terminal logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("optic-spark")

@asynccontextmanager
async def lifespan(app: FastAPI):
    port = os.environ.get("API_PORT", "7070")
    logger.info("🚀 Optic-Spark API Booting Up...")
    logger.info("🔥 Pre-warming Z-Image-Turbo model into VRAM...")
    try:
        await asyncio.to_thread(get_pipeline)
    except Exception as e:
        logger.error(f"❌ Failed to pre-load model: {e}")
        raise e
    logger.info(f"🟢 [SERVER READY] Optic-Spark is listening and ready to accept Webhooks on port {port}!")
    yield
    logger.info("🛑 [SERVER SHUTDOWN] Optic-Spark is powering down...")

app = FastAPI(title="Optic-Spark Z-Image-Turbo API", lifespan=lifespan)

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

@app.get("/health")
async def health():
    """Lightweight readiness probe — returns 200 only after model is pre-warmed."""
    return {"status": "ok", "model": "z-image-turbo"}


@app.post("/generate", response_model=GenerateImageResponse, status_code=202)
async def generate_image(request: GenerateImageRequest, background_tasks: BackgroundTasks):
    job_id = uuid4()

    logger.info(f"📥 [REQUEST RECEIVED] Job: {job_id} | Prompt: '{request.prompt[:40]}...'")

    # Enqueue background task
    background_tasks.add_task(process_image_generation, job_id, request)

    return GenerateImageResponse(job_id=job_id, status="accepted")
