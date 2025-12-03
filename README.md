# XTTS-v2 Voice Server with Llama 3.1

A local TTS server using Coqui's XTTS-v2 model with Llama 3.1 LLM integration via Ollama.

## Features

- **Text-to-Speech**: High-quality voice synthesis with XTTS-v2
- **Voice Cloning**: Clone any voice from a 6-second audio sample
- **LLM Integration**: Chat with Llama 3.1 and get spoken responses
- **Multi-language**: Supports 17 languages
- **Local & Private**: Everything runs on your machine

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Download the model
```bash
python download_model.py
```

### 3. Start Ollama with Llama 3.1
```bash
ollama run llama3.1:8b
```

### 4. Run the server
```bash
python tts_server.py
```

## API Endpoints

### Text to Speech
```bash
curl -X POST http://localhost:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!"}' \
  --output speech.wav
```

### Chat with Voice Response
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke"}' \
  --output response.wav
```

### Chat (Text Only)
```bash
curl -X POST http://localhost:5000/chat/text \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?"}'
```

## Voice Cloning

Provide a reference audio file (6+ seconds) to clone a voice:

```bash
curl -X POST http://localhost:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!", "speaker_wav": "/path/to/voice.wav"}' \
  --output cloned.wav
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Server port |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `LLM_MODEL` | `llama3.1:8b` | LLM model name |

## Supported Languages

XTTS-v2 supports 17 languages:
- English (en), Spanish (es), French (fr), German (de)
- Italian (it), Portuguese (pt), Polish (pl), Turkish (tr)
- Russian (ru), Dutch (nl), Czech (cs), Arabic (ar)
- Chinese (zh-cn), Japanese (ja), Hungarian (hu), Korean (ko), Hindi (hi)

## Model Info

- **Model**: [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)
- **Size**: ~2GB
- **Sample Rate**: 24kHz

## RunPod Deployment

### Option 1: Use Pre-built Template
1. Go to [RunPod Console](https://console.runpod.io)
2. Click "Deploy" → "GPU Pods"
3. Select your GPU (RTX 4090/5090 recommended)
4. Use custom Docker image: `ghcr.io/firmula/xtts-v2-server:latest`
5. Set exposed port: `5000`
6. Deploy!

### Option 2: Build Your Own
```bash
# Clone the repo
git clone https://github.com/firmula/xtts-v2-server.git
cd xtts-v2-server

# Build Docker image
docker build -t xtts-v2-server .

# Push to your registry
docker tag xtts-v2-server your-registry/xtts-v2-server
docker push your-registry/xtts-v2-server
```

### RunPod Template Settings
- **Container Image**: `ghcr.io/firmula/xtts-v2-server:latest`
- **Docker Command**: `python tts_server.py`
- **Exposed Ports**: `5000`
- **Environment Variables**:
  - `PORT=5000`
  - `LLM_MODEL=llama3.1:8b` (optional, if using Ollama)

## License

XTTS-v2 model is licensed under [Coqui Public Model License](https://coqui.ai/cpml).
