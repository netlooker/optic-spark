# Optic-Spark

> A production-grade, asynchronous REST API optimized for NVIDIA DGX Spark (Blackwell) hardware, delivering sub-10-second web graphics using the Z-Image-Turbo GGUF model and a webhook callback architecture.

⚠️ **Hardware Exclusivity:** This project is designed, built, and optimized *exclusively* for the NVIDIA DGX Spark platform powered by the Grace-Blackwell (GB10) superchip. It utilizes hardware-specific memory allocations (`expandable_segments`) and compiles to the Blackwell SM `12.1a` instruction set. It is not intended for standard consumer hardware.

## Features

- **Asynchronous Webhook Architecture:** Designed for AI agents and microservices. Issues an immediate `202 Accepted` HTTP response and delivers the heavy GPU-rendered image asynchronously to a designated webhook URL.
- **Z-Image-Turbo (GGUF):** Utilizes the highly distilled 6-billion parameter single-stream diffusion transformer for sub-10-second inference.
- **Memory Efficient:** Native `diffusers` `from_single_file` loading of the `Q4_K_M` 4-bit quantized model prevents VRAM exhaustion.
- **Containerized for DGX:** Self-contained Docker composition that automatically downloads the required Hugging Face models into a shared volume before booting the API server.

## Installation & Deployment

Deploying Optic-Spark on your DGX Spark machine is fully automated via Docker Compose.

```bash
# Clone the repository
git clone https://github.com/your-org/optic-spark.git
cd optic-spark

# Build and deploy the services
# This will trigger the init-container to download the GGUF model first.
docker compose up -d --build
```

## API Usage

Optic-Spark exposes a single primary endpoint designed for async generation. 

### `POST /generate`

**Request Payload:**
```json
{
  "webhook_url": "https://your-service.com/api/webhook/receiver",
  "prompt": "A highly detailed cyberpunk server room, glowing neon lights, cinematic",
  "aspect_ratio": "16:9",
  "output_format": "webp"
}
```
*(Supported aspect ratios and mapped resolutions: `16:9` (1280x720), `9:16` (720x1280), `1:1` (1024x1024), `4:3` (1024x768), `3:4` (768x1024), `3:2` (1200x800), `2:3` (800x1200))*
*(Supported formats: `webp`, `jpeg`, `png`)*

**Immediate Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted"
}
```

### Webhook Delivery

Once the Grace-Blackwell GPU finishes rendering the image, the background worker will `POST` the final result back to your provided `webhook_url`.

**Success Payload:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "image_url": "https://cdn.optic-spark.local/images/550e8400-e29b-41d4-a716-446655440000.webp"
}
```

**Failure Payload:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_code": "INFERENCE_ERROR",
  "error_hint": "VRAM Exhausted. Try generating a smaller image."
}
```

## OpenAPI Specification

Because Optic-Spark is built on FastAPI, the OpenAPI specification is fully automated.
- **Interactive UI (Swagger):** Navigate to `http://<your-dgx-ip>:7070/docs` once the container is running to test endpoints directly.
- **Static File:** The complete static definition has been exported to the `openapi.yaml` file at the root of the repository, making it plug-and-play for LLMs, autonomous agents, and REST clients.

## Architecture Map

For a quick reference of the API topological map (optimized for LLMs and autonomous agents), please refer to `llms.txt`.
