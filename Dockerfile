FROM nvidia/cuda:13.1.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. System Deps
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates wget ffmpeg \
    python3.11 python3.11-venv python3.11-dev \
    build-essential ninja-build cmake pkg-config \
    libcudnn9-cuda-13 libcudnn9-dev-cuda-13 \
    libavcodec-dev libavformat-dev libavfilter-dev libavdevice-dev libavutil-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Virtual Env
ENV VENV=/opt/venv
RUN python3.11 -m venv $VENV
ENV PATH="$VENV/bin:$PATH"
RUN pip install -U pip setuptools wheel

WORKDIR /app

COPY requirements.txt .

# 3. PyTorch (cu130) exactly as used in wan2gp-spark
RUN pip install --no-cache-dir torch==2.10.0 torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add source code
COPY ./src /app/src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
