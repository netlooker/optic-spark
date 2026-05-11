FROM nvcr.io/nvidia/pytorch:24.01-py3

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# PyTorch is already installed and highly optimized for Grace-Blackwell in this NGC container.
# We just install the remaining API dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Add source code
COPY ./src /app/src

# Internal port – the host-side port is configured via API_PORT in docker-compose.yaml
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
