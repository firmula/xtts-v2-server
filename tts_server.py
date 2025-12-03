#!/usr/bin/env python3
"""
XTTS-v2 TTS Server with Llama 3.1 Integration

This server provides:
1. Text-to-Speech API using XTTS-v2
2. LLM integration with Llama 3.1 via Ollama
3. Voice cloning from reference audio

Endpoints:
- POST /tts - Convert text to speech
- POST /chat - Chat with Llama 3.1 and get audio response
- GET /health - Health check
"""

import os
import io
import json
import wave
import tempfile
import requests
from flask import Flask, request, jsonify, send_file
from TTS.api import TTS

app = Flask(__name__)

# Configuration
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
DEFAULT_SPEAKER = os.path.join(MODEL_DIR, "samples", "en_sample.wav")

# Initialize TTS model (lazy loading)
tts_model = None

def get_tts():
    """Lazy load TTS model."""
    global tts_model
    if tts_model is None:
        print("Loading XTTS-v2 model...")
        tts_model = TTS(
            model_path=MODEL_DIR,
            config_path=os.path.join(MODEL_DIR, "config.json"),
            gpu=False  # Set to True if you have CUDA
        )
        print("XTTS-v2 model loaded!")
    return tts_model


def chat_with_llama(message: str, system_prompt: str = None) -> str:
    """Send message to Llama 3.1 via Ollama and get response."""
    url = f"{OLLAMA_URL}/api/generate"

    prompt = message
    if system_prompt:
        prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"

    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "max_tokens": 150  # Keep responses short for voice
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"Ollama error: {e}")
        return "I'm sorry, I couldn't process that request."


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "model": "xtts-v2",
        "llm": LLM_MODEL
    })


@app.route("/tts", methods=["POST"])
def text_to_speech():
    """
    Convert text to speech.

    Request JSON:
    {
        "text": "Hello, world!",
        "speaker_wav": "/path/to/reference.wav" (optional),
        "language": "en" (optional, default: en)
    }

    Returns: WAV audio file
    """
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data["text"]
    speaker_wav = data.get("speaker_wav", DEFAULT_SPEAKER)
    language = data.get("language", "en")

    try:
        tts = get_tts()

        # Generate audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        tts.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav,
            language=language
        )

        return send_file(
            output_path,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="speech.wav"
        )

    except Exception as e:
        print(f"TTS error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat_with_voice():
    """
    Chat with Llama 3.1 and get audio response.

    Request JSON:
    {
        "message": "What is the weather like?",
        "speaker_wav": "/path/to/reference.wav" (optional),
        "system_prompt": "You are a helpful assistant." (optional)
    }

    Returns: WAV audio file with spoken response
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    message = data["message"]
    speaker_wav = data.get("speaker_wav", DEFAULT_SPEAKER)
    system_prompt = data.get("system_prompt", "You are a helpful voice assistant. Keep your responses brief and conversational.")

    try:
        # Get LLM response
        print(f"User: {message}")
        llm_response = chat_with_llama(message, system_prompt)
        print(f"Assistant: {llm_response}")

        # Convert to speech
        tts = get_tts()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        tts.tts_to_file(
            text=llm_response,
            file_path=output_path,
            speaker_wav=speaker_wav,
            language="en"
        )

        return send_file(
            output_path,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="response.wav"
        )

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chat/text", methods=["POST"])
def chat_text_only():
    """
    Chat with Llama 3.1 and get text response (no audio).

    Request JSON:
    {
        "message": "What is the weather like?",
        "system_prompt": "You are a helpful assistant." (optional)
    }

    Returns: JSON with text response
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    message = data["message"]
    system_prompt = data.get("system_prompt", "You are a helpful voice assistant. Keep your responses brief and conversational.")

    try:
        llm_response = chat_with_llama(message, system_prompt)
        return jsonify({
            "message": message,
            "response": llm_response
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           XTTS-v2 TTS Server with Llama 3.1                  ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                   ║
║    POST /tts        - Text to speech                         ║
║    POST /chat       - Chat + voice response                  ║
║    POST /chat/text  - Chat (text only)                       ║
║    GET  /health     - Health check                           ║
╠══════════════════════════════════════════════════════════════╣
║  Running on: http://localhost:{port:<5}                          ║
║  LLM Model:  {LLM_MODEL:<20}                        ║
╚══════════════════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=port, debug=False)
