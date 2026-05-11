# Optic-Spark Native CLI Skill

## Overview
You are equipped with the ability to generate stunning, photorealistic web graphics using the Optic-Spark inference engine (powered by Z-Image-Turbo on NVIDIA DGX Blackwell hardware).

Instead of orchestrating asynchronous webhook callbacks manually, you can use the **Optic-Spark Native CLI** (`optic-cli`). The CLI automatically spins up an ephemeral receiver, dispatches the prompt, blocks until the GPU finishes rendering, and downloads the final image to your local directory.

## Execution Flow

To generate an image, simply execute the `optic-cli` binary.

### Command Syntax

```bash
./optic-cli --prompt "<highly detailed description>" [OPTIONS]
```

**Options:**
- `--prompt`: (Required) The text description of the desired image.
- `--aspect`: Aspect ratio. Strict buckets: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`. (Default: `1:1`)
- `--format`: Output file format: `png`, `webp`, `jpeg`. (Default: `png`)
- `--out`: Output directory where the final image will be saved. (Default: current directory `.`)
- `--api`: Base URL of the Optic-Spark API. (Default: `http://localhost:7070`)
- `--callback-host`: Host IP/domain for the API to reach the CLI's ephemeral webhook receiver. (Default: `http://host.docker.internal` for Docker on Mac; use `http://127.0.0.1` for host networking).

### Example Usage

```bash
cd cli/
./optic-cli --prompt "A highly detailed cyberpunk server room, glowing neon lights, cinematic" --aspect 16:9 --format png --out ./images
```

The CLI will block for 8-10 seconds while the Grace-Blackwell inference runs. Once complete, it will output:
`💾 Saved to: images/20260511_123045_a_highly_detailed_cyberpunk_server.png`
`🎉 All done!`

## Prompting Guide (Z-Image-Turbo Specifics)

Z-Image-Turbo operates differently than classic Stable Diffusion. When crafting your `--prompt`, you **must** adhere to these architectural quirks:

1. **No Negative Prompts:** The model runs at a `guidance_scale` of `0.0` and entirely ignores negative prompts.
2. **Positive Constraints:** You must encode what you *don't* want into the positive prompt using explicit constraints at the end of the prompt.
   - *Example:* `"...plain background, no text, no watermark, no logos, no extra limbs."`
3. **Safety & Modesty:** To avoid NSFW or biased generations, be explicit about age, clothing, and coverage.
   - *Example:* `"...adult woman, wearing a modest business suit, fully clothed..."`
4. **Prompt Structure:** The model thrives on detailed, 80-250 word prompts. Use this scaffold for the best results:
   `[Shot & subject] + [Age & appearance] + [Clothing] + [Environment/background] + [Lighting] + [Mood] + [Style] + [Cleanup constraints]`

*Example Perfect Prompt:*
> "A medium-shot portrait of an adult woman in her 30s, natural look, medium-length brown hair, wearing a dark business suit and shirt, fully clothed, modest professional outfit, standing in a modern office with a soft blurred background, soft diffused daylight, calm confident expression, realistic photography, 50mm lens, 4K quality, plain background, no logos, no text, no watermark."
