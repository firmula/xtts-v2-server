#!/bin/bash
# =============================================================================
# RUNPOD HOTLINE SETUP SCRIPT
# =============================================================================
# Run this script on your RunPod instance to set up the full AI hotline stack.
#
# Usage:
#   chmod +x setup_runpod.sh
#   ./setup_runpod.sh
# =============================================================================

set -e

echo "=========================================="
echo "  AI HOTLINE SETUP FOR RUNPOD"
echo "=========================================="

# 1. Update system
echo "[1/8] Updating system..."
apt update && apt install -y python3.11 python3.11-venv python3.11-dev git curl

# 2. Create Python 3.11 virtual environment
echo "[2/8] Creating Python 3.11 environment..."
python3.11 -m venv /workspace/hotline-env
source /workspace/hotline-env/bin/activate

# 3. Install Python dependencies
echo "[3/8] Installing Python dependencies..."
pip install --upgrade pip
pip install TTS flask flask-cors requests huggingface_hub

# 4. Clone the repository
echo "[4/8] Cloning repository..."
if [ -d "/workspace/xtts-v2-server" ]; then
    echo "Repository already exists, pulling latest..."
    cd /workspace/xtts-v2-server && git pull
else
    git clone https://github.com/firmula/xtts-v2-server.git /workspace/xtts-v2-server
fi
cd /workspace/xtts-v2-server

# 5. Download XTTS-v2 model
echo "[5/8] Downloading XTTS-v2 model (~2GB)..."
python download_model.py

# 6. Install Ollama
echo "[6/8] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 7. Pull Llama 3.1
echo "[7/8] Pulling Llama 3.1 model..."
ollama serve &
sleep 5
ollama pull llama3.1:8b

# 8. Install Langflow
echo "[8/8] Installing Langflow..."
pip install langflow

echo ""
echo "=========================================="
echo "  SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "To start all services, run:"
echo ""
echo "  # Terminal 1: Start Ollama"
echo "  ollama serve"
echo ""
echo "  # Terminal 2: Start TTS Server (port 5000)"
echo "  source /workspace/hotline-env/bin/activate"
echo "  cd /workspace/xtts-v2-server"
echo "  python tts_server.py"
echo ""
echo "  # Terminal 3: Start Webhook Server (port 8080)"
echo "  source /workspace/hotline-env/bin/activate"
echo "  cd /workspace/xtts-v2-server/webhook"
echo "  python hotline_server.py"
echo ""
echo "  # Terminal 4: Start Langflow (port 7860)"
echo "  source /workspace/hotline-env/bin/activate"
echo "  langflow run --host 0.0.0.0 --port 7860"
echo ""
echo "Then expose these ports in RunPod:"
echo "  - 5000  (TTS Server)"
echo "  - 8080  (Webhook Server - configure in Twilio)"
echo "  - 7860  (Langflow UI)"
echo "  - 11434 (Ollama API)"
echo ""
echo "=========================================="
