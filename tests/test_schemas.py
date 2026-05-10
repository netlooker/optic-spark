import pytest
from pydantic import ValidationError

from src.schemas import GenerateImageRequest, GenerateImageResponse, WebhookDeliveryPayload


def test_generate_image_request_valid():
    request = GenerateImageRequest(
        webhook_url="https://example.com/webhook",
        prompt="A test image",
        aspect_ratio="16:9",
        output_format="webp"
    )
    assert request.aspect_ratio == "16:9"
    assert request.output_format == "webp"

def test_generate_image_request_invalid_aspect_ratio():
    with pytest.raises(ValidationError):
        GenerateImageRequest(
            webhook_url="https://example.com/webhook",
            prompt="A test image",
            aspect_ratio="1:2", # Invalid
            output_format="webp"
        )

def test_generate_image_request_invalid_format():
    with pytest.raises(ValidationError):
        GenerateImageRequest(
            webhook_url="https://example.com/webhook",
            prompt="A test image",
            aspect_ratio="1:1",
            output_format="gif" # Invalid
        )

def test_generate_image_response():
    response = GenerateImageResponse(
        job_id="123e4567-e89b-12d3-a456-426614174000",
        status="accepted"
    )
    assert response.status == "accepted"

def test_webhook_payload_completed():
    payload = WebhookDeliveryPayload(
        job_id="123e4567-e89b-12d3-a456-426614174000",
        status="completed",
        image_url="https://example.com/image.webp"
    )
    assert payload.status == "completed"
    assert str(payload.image_url) == "https://example.com/image.webp"

def test_webhook_payload_failed():
    payload = WebhookDeliveryPayload(
        job_id="123e4567-e89b-12d3-a456-426614174000",
        status="failed",
        error_code="VRAM_EXHAUSTED",
        error_hint="Try generating a smaller image."
    )
    assert payload.status == "failed"
    assert payload.error_code == "VRAM_EXHAUSTED"
