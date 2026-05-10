from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Literal, Optional
from uuid import UUID

class GenerateImageRequest(BaseModel):
    webhook_url: HttpUrl = Field(..., description="The URL where the final image result will be POSTed.")
    prompt: str = Field(..., min_length=1, max_length=2000, description="The text description of the desired image.")
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"] = Field(
        default="1:1", description="Strictly enforced aspect ratios for web graphics."
    )
    output_format: Literal["webp", "jpeg", "png"] = Field(
        default="png", description="Desired file format for the output image."
    )

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt must not be blank or whitespace-only")
        return v

class GenerateImageResponse(BaseModel):
    job_id: UUID = Field(..., description="A unique identifier for tracking the generation job.")
    status: Literal["accepted"] = Field(..., description="Indicates the job has been queued.")

class WebhookDeliveryPayload(BaseModel):
    job_id: UUID
    status: Literal["completed", "failed"]
    image_url: Optional[HttpUrl] = Field(None, description="The URL to download the generated image (if successful).")
    error_code: Optional[str] = Field(None, description="Semantic error code if the job failed.")
    error_hint: Optional[str] = Field(None, description="Plain-text resolution hint for AI agent retry.")
