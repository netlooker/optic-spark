from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_generate_endpoint_success():
    payload = {
        "webhook_url": "https://example.com/webhook",
        "prompt": "A test image",
        "aspect_ratio": "16:9",
        "output_format": "webp"
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "accepted"

def test_generate_endpoint_invalid_payload():
    payload = {
        "webhook_url": "not-a-url",
        "prompt": "A test image",
        "aspect_ratio": "16:9",
        "output_format": "webp"
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 422
