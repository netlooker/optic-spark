# optic-spark: Product Requirements & Architecture Document (PRD)

## 1. Product Vision and MVP Scope
`optic-spark` is a standalone, production-grade REST API service dedicated to generating high-quality, web-optimized graphics. Deployed on the NVIDIA DGX Spark platform powered by the Grace-Blackwell (GB10) superchip, the system must leverage extreme hardware optimizations to deliver high-throughput generation for autonomous AI agents and enterprise clients.

### 1.1 Model Selection and MVP Strategy
Initial architectural exploration evaluated supporting both ERNIE-Image-Turbo and Z-Image-Turbo simultaneously. However, deep architectural analysis reveals that the two models are fundamentally disparate in their component structures:
- **ERNIE-Image-Turbo**: Utilizes an 8B parameter single-stream Diffusion Transformer (DiT) that requires a separate, external Ministral 3.3B text encoder and a separate Flux.2 VAE to function properly within a pipeline.
- **Z-Image-Turbo**: Features an architecture where the required text encoders (both T5 and CLIP) and the VAE are fully embedded directly into the model weights, completely eliminating the need to load separate components.

Because these architectures demand entirely different Diffusers pipeline classes and memory management strategies, implementing both simultaneously introduces excessive complexity for an initial release.

**MVP Decision**: Phase 1 of optic-spark will launch exclusively with **Z-Image-Turbo** to guarantee high-speed, sub-10-second generation. ERNIE-Image-Turbo support is deferred to Phase 2, though the API will be designed to support it polymorphically from day one.

## 2. API-First and OpenAPI 3.1 Design Principles

### 2.1 Asynchronous Generation Architecture
Because image generation inherently takes seconds to complete, a synchronous API risks connection timeouts and thread pool exhaustion. optic-spark will enforce a strict asynchronous webhook/callback architecture:
- **Request**: The client submits a generation request containing a `webhook_url`.
- **Immediate Response**: The API responds instantly with HTTP `202 Accepted` and a unique `job_id`.
- **Delivery**: Upon completion, the background worker issues an HTTP `POST` to the client's `webhook_url` containing the finalized image URL. This entirely eliminates wasteful client polling loops.

### 2.2 Future-Proof Polymorphic Schema Design
While the MVP only serves Z-Image-Turbo, the OpenAPI 3.1 schema must be designed for a multi-model future. The API payload will utilize the `oneOf` keyword combined with a discriminator property (`model_type`).
By explicitly mapping `model_type: z-image` or `model_type: ernie`, the validation layer can strictly enforce parameter requirements without guessing. For example, Z-Image-Turbo schemas will enforce specific guidance scales, while ERNIE schemas will eventually introduce its native Prompt Enhancer (`use_pe`) fields.

## 3. AI Agentic-Ready Interface Design
To ensure autonomous AI agents can easily discover and consume the optic-spark API, the service will implement the following agentic-ready principles:
- **Discoverability via llms.txt**: The root domain will host an `llms.txt` markdown file. This provides agents with a plain-text, highly readable topological map of the API's endpoints, capabilities, and constraints without forcing them to parse massive JSON OpenAPI schemas.
- **Model Context Protocol (MCP)**: The service will expose its capabilities via an MCP server, acting as a standardized integration layer that allows agents (like Claude or enterprise chatbots) to securely discover and invoke the image generation tools.
- **Tool-Calling Metadata**: OpenAPI descriptions will act as embedded prompt engineering. Descriptions will explicitly state limitations (e.g., "Generates raster images only, not SVGs") to prevent hallucinated invocations.
- **Semantic Error Handling**: Errors will not return generic 500 status codes. The API will return highly structured JSON envelopes containing specific `error_code` strings (e.g., `VRAM_EXHAUSTED`), standard HTTP status codes (e.g., `422 Unprocessable Entity`), and plain-text resolution hints instructing the agent on how to adjust its parameters for a retry.

## 4. Model Quantization and Serving Pipeline (Z-Image-Turbo)
To maximize concurrent request throughput on the MVP, optic-spark will leverage aggressive block-wise quantization.
- **GGUF Integration**: Z-Image-Turbo will be loaded using the GGUF file format via HuggingFace diffusers (supported via the `from_single_file` mixin under PR-12756).
- **Memory Efficiency**: We will deploy the `Q4_K_M` (4-bit) quantized variant. This dramatically reduces VRAM consumption compared to the baseline FP16 precision, while suffering virtually no aesthetic degradation, making it the optimal sweet spot for production deployments.

## 5. Hardware Optimization for NVIDIA DGX Spark (GB10)
The GB10 architecture requires specific, low-level tuning to bypass legacy discrete-GPU defaults and leverage its massive unified memory topology.
- **Unified Memory Protection**: The DGX Spark shares 128GB of memory between the CPU and GPU. Standard PyTorch memory fragmentation can cause the system to freeze in a "zombie" state rather than cleanly throwing an Out-Of-Memory error. To fix this, the environment must strictly export `PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"`.
- **Architecture Compilation Flags**: The system must export `TORCH_CUDA_ARCH_LIST="12.1a"` to ensure the compiler generates machine code specific to the Blackwell SM 12.1a instruction set.
- **Attention Backends**: PyTorch's native Scaled Dot Product Attention (SDPA) paired with the latest cuDNN backend has proven to be extraordinarily fast on GB10 silicon for diffusion models, often outperforming default flash_attention_2 implementations on this specific hardware.

## 6. Website Graphics Optimization Pipeline
Because optic-spark is dedicated to website graphics, the payloads must be optimized for network delivery and browser rendering.
- **Strict Resolution Constraints**: The API will reject arbitrary pixel dimensions, strictly enforcing standard trained aspect ratio buckets via Enum validation to prevent latent space hallucinations and structural anomalies. To support standard web graphics, the following Z-Image-Turbo optimal resolution buckets will be strictly enforced: 1:1 (1024x1024), 16:9 (1280x720), 9:16 (720x1280), 4:3 (1152x864), 3:4 (864x1152), 3:2 (1248x832), and 2:3 (832x1248).
- **Configurable Format Selection**: The API payload will expose an `output_format` parameter, allowing the client to dynamically select the desired file format (e.g., `webp`, `jpeg`, or `png`) based on their specific web deployment needs, rather than forcing a single format.
- **nvImageCodec Execution**: We will utilize the high-performance `nvidia-nvimgcodec` library to handle the client-requested formats. It is important to note the hardware execution boundaries: if the client requests `jpeg`, the encoding will be hardware-accelerated directly on the Blackwell GPU using the CUDA jpeg encoder. However, if the client requests `webp` or `png`, the encoding will fall back to CPU-only execution. To prevent blocking the main GPU inference pipeline, these CPU-bound WebP and PNG encoding tasks will be securely offloaded to a dedicated, asynchronous background thread pool running on the 20-core Grace ARM CPU.
