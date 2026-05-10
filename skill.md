# Optic-Spark Generation Skill

## Overview
You are equipped with the ability to generate stunning, photorealistic web graphics using the Optic-Spark inference engine (powered by Z-Image-Turbo on NVIDIA DGX Blackwell hardware). 

Because image generation takes around 8-10 seconds and consumes heavy GPU resources, this API uses a **strictly asynchronous, webhook-based architecture**. You cannot wait for the HTTP response to contain your image. You must provide a webhook URL that the DGX machine will call when the image is ready.

## Execution Flow

To generate an image, follow these 3 steps exactly:

### Step 1: Request Generation
Send an HTTP `POST` request to the Optic-Spark API's `/generate` endpoint.
- **Endpoint:** `POST http://<optic-spark-host>:7070/generate`
- **Headers:** `Content-Type: application/json`

**Payload Schema:**
```json
{
  "webhook_url": "<YOUR_WEBHOOK_RECEIVER_URL>",
  "prompt": "<highly detailed description of the image>",
  "aspect_ratio": "16:9",
  "output_format": "webp"
}
```
*Note on `aspect_ratio`: You MUST select from the following strict buckets: `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`, `"3:2"`, or `"2:3"`.*
*Note on `output_format`: You MUST select from: `"webp"`, `"jpeg"`, or `"png"`.*

**Expected Response:** You will instantly receive an `HTTP 202 Accepted`.
```json
{
  "job_id": "uuid-string",
  "status": "accepted"
}
```

### Step 2: Await Webhook Callback
Do not poll the server. Suspend your local operation or proceed with other tasks. The Optic-Spark background worker will send an HTTP `POST` request back to your `<YOUR_WEBHOOK_RECEIVER_URL>` when the GPU has finished.

**Success Callback Payload:**
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "image_url": "http://<optic-spark-host>:7070/output/20260510_1234_slug_uuid.webp"
}
```

**Failure Callback Payload:**
```json
{
  "job_id": "uuid-string",
  "status": "failed",
  "error_code": "INFERENCE_ERROR",
  "error_hint": "String describing the failure"
}
```

### Step 3: Retrieve the Image
Once you receive a `completed` webhook payload, extract the `image_url`. Execute a standard `HTTP GET` request against this URL to stream and download the actual image bytes into your system.

## Prompting Guide (Z-Image-Turbo Specifics)

Z-Image-Turbo operates differently than classic Stable Diffusion. When generating the `prompt` string for your API request, you **must** adhere to these architectural quirks:

1. **No Negative Prompts:** The model runs at a `guidance_scale` of `0.0` and entirely ignores negative prompts.
2. **Positive Constraints:** You must encode what you *don't* want into the positive prompt using explicit constraints at the end of the prompt.
   - *Example:* `"...plain background, no text, no watermark, no logos, no extra limbs."`
3. **Safety & Modesty:** To avoid NSFW or biased generations, be explicit about age, clothing, and coverage.
   - *Example:* `"...adult woman, wearing a modest business suit, fully clothed..."`
4. **Prompt Structure:** The model thrives on detailed, 80-250 word prompts. Use this scaffold for the best results:
   `[Shot & subject] + [Age & appearance] + [Clothing] + [Environment/background] + [Lighting] + [Mood] + [Style] + [Cleanup constraints]`

*Example Perfect Prompt:*
> "A medium-shot portrait of an adult woman in her 30s, natural look, medium-length brown hair, wearing a dark business suit and shirt, fully clothed, modest professional outfit, standing in a modern office with a soft blurred background, soft diffused daylight, calm confident expression, realistic photography, 50mm lens, 4K quality, plain background, no logos, no text, no watermark."
