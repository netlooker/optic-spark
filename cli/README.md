# optic-cli

A native, zero-dependency CLI client for the [Optic-Spark](../) image generation API.

Instead of manually orchestrating async webhook callbacks, `optic-cli` handles everything transparently:
it spins up an ephemeral local HTTP receiver, dispatches the generation request, **blocks until the GPU finishes**, downloads the image, and exits — all in a single command.

---

## Requirements

- **Go 1.19+** (only needed to compile; the resulting binary has no runtime dependencies)
- A running **Optic-Spark API** instance reachable from this machine

---

## Build

```bash
cd cli/
go build -o optic-cli main.go
```

This produces a single static binary with no external dependencies. Cross-compile for Linux ARM64 (DGX Spark) from macOS:

```bash
GOOS=linux GOARCH=arm64 go build -o optic-cli-linux-arm64 main.go
```

---

## Usage

```bash
./optic-cli --prompt "<image description>" [OPTIONS]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` | *(required)* | Text description of the image to generate |
| `--aspect` | `1:1` | Aspect ratio. Must be one of: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3` |
| `--format` | `png` | Output file format: `png`, `webp`, `jpeg` |
| `--out` | `.` | Directory where the final image is saved |
| `--api` | `http://localhost:7070` | Base URL of the Optic-Spark API |
| `--callback-host` | `http://host.docker.internal` | Publicly reachable host/IP for the API to deliver the webhook back to this machine |

### `--callback-host` explained

The CLI starts a temporary HTTP server on a **random free port** and registers it as the webhook receiver. The `--callback-host` flag tells the DGX what IP/hostname to use to reach that server:

| Scenario | Value to use |
|----------|-------------|
| Running CLI on the same host as Docker (Mac/Windows) | `http://host.docker.internal` *(default)* |
| Running CLI directly on the DGX (host networking) | `http://127.0.0.1` |
| Running CLI on a remote machine | `http://<your-machine-ip>` |

---

## Examples

```bash
# Basic – 1:1 square, saved to current directory
./optic-cli --prompt "A glowing cyberpunk server room, neon lights, cinematic"

# 16:9 widescreen, saved to ./images/
./optic-cli \
  --prompt "A massive Grace-Blackwell GPU cluster, hyperrealistic render, dramatic lighting" \
  --aspect 16:9 \
  --out ./images

# Remote API on the DGX Spark
./optic-cli \
  --api http://192.168.1.42:7070 \
  --callback-host http://192.168.1.10 \
  --prompt "Abstract neural network visualization, deep blues and purples"

# WebP format for web delivery
./optic-cli --prompt "Product shot, white background, minimal" --format webp --out ./dist
```

### Expected Output

```
🚀 Dispatching request to http://localhost:7070/generate...
📡 Listening for webhook on http://host.docker.internal:54321/webhook...
⏳ Waiting for Grace-Blackwell inference...

✅ Image generated successfully! Downloading...
💾 Saved to: images/20260511_123045_a_massive_grace_blackwell_gpu.png
🎉 All done!
```

---

## Testing

The test suite uses Go's built-in `net/http/httptest` to mock both the Optic-Spark API and the image file server — **no real network or GPU required**.

```bash
cd cli/
go test -v ./...
```

| Test | Coverage |
|------|---------|
| `TestDownloadImage_Success` | File saved with correct name and bytes |
| `TestDownloadImage_BadStatus` | 404 → returns `bad status` error |
| `TestDownloadImage_NetworkError` | Unreachable host → returns error |
| `TestDownloadImage_CreatesOutputDir` | Nested output dirs created automatically |
| `TestWebhookHandler_CompletedPayload` | Completed payload → image downloaded, signals success |
| `TestWebhookHandler_FailedPayload` | Failed payload → signals failure, no download |
| `TestWebhookHandler_WrongMethod` | GET request → `405 Method Not Allowed` |
| `TestWebhookHandler_InvalidJSON` | Malformed body → `400 Bad Request` |
| `TestWebhookHandler_DownloadFailure` | Completed job but broken image URL → signals failure |

---

## For AI Agents

See [`skill.md`](./skill.md) for a concise, agent-optimized instruction set covering execution flow, all flags, and prompting best practices.
