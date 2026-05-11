#!/usr/bin/env bash

# ============================================================
# Optic-Spark — DGX Spark (GB10 Grace-Blackwell) Launch Script
# ============================================================

# === Configuration ===
API_PORT=7070
PROJECT_DIR="/home/netlooker/optic-spark"

# === GB10 Optimizations ===
apply_spark_optimizations() {
  echo "========================================================"
  echo "⚡ Applying DGX Spark (GB10) optimizations..."

  # Persistence mode: eliminates cold-start latency on first inference
  sudo nvidia-smi -pm 1 >/dev/null 2>&1

  # Clock capping: prevents OCP (Over-Current Protection) shutdowns
  # 300-2100 MHz is the stable Goldilocks zone for Blackwell workloads
  sudo nvidia-smi -lgc 300,2100 >/dev/null 2>&1

  # Disable swap: required for Unified Memory / NVLink consistency
  sudo swapoff -a >/dev/null 2>&1

  echo "   GPU Clocks : 300-2100 MHz (OCP Protection Active)"
  echo "   Swap       : Disabled (Unified Memory Mode)"
  echo "   Persistence: Enabled (Low-latency Mode)"
  echo "========================================================"
}

# === Graceful Shutdown ===
cleanup() {
  echo ""
  echo "🛑 Shutdown signal received. Powering down Optic-Spark..."
  cd "${PROJECT_DIR}"
  docker compose down >/dev/null 2>&1
  exit 0
}

trap cleanup INT TERM HUP QUIT EXIT

# === Main ===
apply_spark_optimizations

cd "${PROJECT_DIR}" || { echo "❌ Project dir not found: ${PROJECT_DIR}"; exit 1; }

echo "🚀 Launching Optic-Spark API (streaming logs)..."
echo "⏳ Waiting for Z-Image-Turbo to pre-warm into VRAM..."
echo "   (First boot downloads auxiliary model components ~5-8 GB)"
echo ""

# Run compose in foreground (streams logs live) in a background subshell
docker compose up &
COMPOSE_PID=$!

# Poll /health in parallel — print banner as soon as model is ready
MAX_WAIT=600
SECONDS_WAITED=0
while ! curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1; do
  if [ "${SECONDS_WAITED}" -ge "${MAX_WAIT}" ]; then
    echo ""
    echo "❌ Timed out after ${MAX_WAIT}s waiting for API. Check logs above."
    exit 1
  fi
  sleep 5
  SECONDS_WAITED=$((SECONDS_WAITED + 5))
done

echo ""
echo "========================================================"
echo "✅ OPTIC-SPARK IS ONLINE!"
echo ""
echo "🌐 API     : http://$(hostname -I | awk '{print $1}'):${API_PORT}"
echo "📖 Docs    : http://$(hostname -I | awk '{print $1}'):${API_PORT}/docs"
echo "❤️  Health  : http://$(hostname -I | awk '{print $1}'):${API_PORT}/health"
echo ""
echo "   Generate an image:"
echo "   ./cli/optic-cli \\"
echo "     --api http://$(hostname -I | awk '{print $1}'):${API_PORT} \\"
echo "     --callback-host http://<your-client-ip> \\"
echo "     --prompt \"A cyberpunk city at night, neon lights\" \\"
echo "     --aspect 16:9"
echo "========================================================"

# Keep alive — stream logs to terminal
docker compose logs -f optic-spark-api
