# Changelog

All notable changes to Optic-Spark will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-05-11

### Added
- Asynchronous `POST /generate` REST endpoint returning `HTTP 202 Accepted`
- Webhook-based image delivery: the DGX worker POSTs a JSON payload to the caller's `webhook_url` on completion
- Z-Image-Turbo GGUF (Q4_K_M quantization) inference engine via Diffusers `from_single_file`
- Support for 7 popular web aspect ratios: `16:9` (1280×720), `9:16` (720×1280), `1:1` (1024×1024), `4:3` (1024×768), `3:4` (768×1024), `3:2` (1200×800), `2:3` (800×1200)
- Output formats: `webp` (default), `jpeg`, `png`
- Meaningful slugified filenames: `{timestamp}_{prompt_slug}_{short_uuid}.{ext}`
- Static file serving of generated images at `/output/<filename>`
- GPU lock (`asyncio.Lock`) preventing concurrent CUDA executions and VRAM OOM
- Thread-safe double-checked locking for the model singleton (`threading.Lock`)
- Model pre-warming on startup — server only marks itself READY after model is in VRAM
- `aiohttp.ClientTimeout(total=15)` on webhook delivery to prevent hanging connections
- Differentiated webhook error codes: `MODEL_NOT_FOUND` vs `INFERENCE_ERROR`
- Prompt validation: blank/whitespace-only prompts rejected at schema level
- Configurable host port via `API_PORT` env var (default `7070`)
- Configurable `BASE_URL` for correct image URL construction in webhook payloads
- Structured terminal logging with emoji lifecycle events across all modules
- Static `openapi.yaml` exported at repo root for agent/tooling integration
- `skill.md` — step-by-step agent integration guide including Z-Image-Turbo prompting best practices
- `llms.txt` — compact API reference for LLM context windows
- Docker Compose with `init-model-downloader` service (skips download if model already cached)
- Dockerfile targeting `nvidia/cuda:12.1.1-devel-ubuntu22.04` with Blackwell optimisation flags
- TDD test suite: 27 tests across schemas, API routes, engine, and worker
- `tests/conftest.py` stubs all GPU/ML dependencies for CI-clean test execution
