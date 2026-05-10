"""Tests for the worker module: filename generation and pipeline error handling."""
import pytest
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch
from src.worker import generate_filename


# ─────────────────────────────────────────────
# generate_filename
# ─────────────────────────────────────────────

class TestGenerateFilename:
    JOB_ID = UUID("123e4567-e89b-12d3-a456-426614174000")

    def test_extension_is_appended(self):
        result = generate_filename("a prompt", self.JOB_ID, "webp")
        assert result.endswith(".webp")

    def test_short_uuid_present(self):
        result = generate_filename("a prompt", self.JOB_ID, "webp")
        # First 8 chars of UUID: "123e4567"
        assert "123e4567" in result

    def test_slug_uses_first_five_words(self):
        result = generate_filename("one two three four five six seven", self.JOB_ID, "png")
        # Only first 5 words should appear; "six" and "seven" must not
        assert "six" not in result
        assert "seven" not in result

    def test_slug_strips_special_characters(self):
        result = generate_filename("hello! world @ 2025", self.JOB_ID, "jpeg")
        # Special chars should be removed from slug segment
        assert "!" not in result
        assert "@" not in result

    def test_empty_prompt_does_not_raise(self):
        # An empty prompt should produce a valid filename (just timestamp + uuid)
        result = generate_filename("", self.JOB_ID, "webp")
        assert result.endswith(".webp")
        assert "123e4567" in result

    def test_unicode_prompt_does_not_raise(self):
        # Non-ASCII chars should be stripped silently
        result = generate_filename("café résumé 日本語", self.JOB_ID, "webp")
        assert result.endswith(".webp")


# ─────────────────────────────────────────────
# process_image_generation – failure path
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_image_generation_inference_failure_sends_failed_webhook():
    """If inference throws, worker must still dispatch a 'failed' webhook payload."""
    from src.schemas import GenerateImageRequest
    from src.worker import process_image_generation
    import uuid

    job_id = uuid.uuid4()
    request = GenerateImageRequest(
        webhook_url="https://example.com/webhook",
        prompt="test prompt",
        aspect_ratio="1:1",
        output_format="webp",
    )

    mock_response = MagicMock()
    mock_response.status = 200
    mock_post = AsyncMock(return_value=mock_response)
    mock_post.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("src.worker.asyncio.to_thread", side_effect=RuntimeError("GPU exploded")), \
         patch("src.worker.aiohttp.ClientSession", return_value=mock_session):
        await process_image_generation(job_id, request)

    # Verify that post was called with a failed payload
    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
    assert payload["status"] == "failed"
    assert payload["error_code"] == "INFERENCE_ERROR"
