#!/usr/bin/env python3
"""
AI Hotline Webhook Server

This server handles incoming calls from Twilio/Jambonz and orchestrates:
1. Speech-to-Text (Whisper)
2. AI Response (Langflow or direct Ollama/Llama 3.1)
3. Text-to-Speech (XTTS-v2)

Endpoints:
- POST /voice          - Twilio webhook (TwiML)
- POST /jambonz        - Jambonz webhook
- POST /gather         - Handle speech input
- GET  /health         - Health check
- GET  /audio/<file>   - Serve generated audio
"""

import os
import io
import json
import uuid
import tempfile
import requests
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =============================================================================
# CONFIGURATION
# =============================================================================

PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")

# Service URLs
TTS_URL = os.getenv("TTS_URL", "http://localhost:5000")
ASR_URL = os.getenv("ASR_URL", "http://localhost:9000")
LLM_URL = os.getenv("LLM_URL", "http://localhost:11434")
LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860")
LANGFLOW_FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "")  # Set this to use Langflow

# Audio cache
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./audio_cache"))
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# System prompt for the AI assistant
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """You are a helpful AI voice assistant.
Keep your responses brief and conversational - aim for 1-2 sentences.
You're speaking on a phone call, so be natural and friendly.""")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def call_tts(text: str, language: str = "en") -> str:
    """Convert text to speech using XTTS-v2, return audio URL."""
    try:
        response = requests.post(
            f"{TTS_URL}/tts",
            json={"text": text, "language": language},
            timeout=30
        )
        response.raise_for_status()

        # Save audio file
        audio_id = str(uuid.uuid4())
        audio_path = AUDIO_DIR / f"{audio_id}.wav"
        audio_path.write_bytes(response.content)

        return f"{BASE_URL}/audio/{audio_id}.wav"
    except Exception as e:
        print(f"TTS error: {e}")
        return None


def call_asr(audio_data: bytes) -> str:
    """Convert speech to text using Whisper."""
    try:
        files = {"audio_file": ("audio.wav", audio_data, "audio/wav")}
        response = requests.post(
            f"{ASR_URL}/asr",
            files=files,
            data={"task": "transcribe", "language": "en"},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("text", "")
    except Exception as e:
        print(f"ASR error: {e}")
        return ""


def call_llm(message: str, conversation_history: list = None) -> str:
    """Get AI response from Ollama/Llama 3.1 or Langflow."""

    # If Langflow flow ID is set, use Langflow
    if LANGFLOW_FLOW_ID:
        return call_langflow(message)

    # Otherwise, use Ollama directly
    try:
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {message}\nAssistant:"

        response = requests.post(
            f"{LLM_URL}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 150  # Keep responses short
                }
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "I couldn't process that.")
    except Exception as e:
        print(f"LLM error: {e}")
        return "I'm sorry, I had trouble understanding. Could you repeat that?"


def call_langflow(message: str) -> str:
    """Get AI response from Langflow workflow."""
    try:
        response = requests.post(
            f"{LANGFLOW_URL}/api/v1/run/{LANGFLOW_FLOW_ID}",
            json={
                "input_value": message,
                "output_type": "chat",
                "input_type": "chat"
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        # Extract text from Langflow response
        outputs = result.get("outputs", [{}])
        if outputs:
            return outputs[0].get("outputs", [{}])[0].get("results", {}).get("message", {}).get("text", "")
        return "I couldn't process that through the workflow."
    except Exception as e:
        print(f"Langflow error: {e}")
        return "I'm having trouble with my AI workflow. Please try again."


# =============================================================================
# TWILIO ENDPOINTS (TwiML)
# =============================================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "ai-hotline-webhook",
        "services": {
            "tts": TTS_URL,
            "asr": ASR_URL,
            "llm": LLM_URL,
            "langflow": LANGFLOW_URL if LANGFLOW_FLOW_ID else "not configured"
        }
    })


@app.route("/voice", methods=["POST"])
def twilio_voice():
    """
    Twilio voice webhook - called when someone calls your number.
    Returns TwiML to greet and gather speech input.
    """
    call_sid = request.form.get("CallSid", "unknown")
    from_number = request.form.get("From", "unknown")

    print(f"[INCOMING CALL] SID: {call_sid}, From: {from_number}")

    # Generate greeting audio
    greeting = "Hello! I'm your AI assistant. How can I help you today?"
    audio_url = call_tts(greeting)

    if audio_url:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Gather input="speech" action="{BASE_URL}/gather" method="POST"
            speechTimeout="auto" language="en-US">
        <Say>I'm listening.</Say>
    </Gather>
    <Say>I didn't hear anything. Goodbye!</Say>
    <Hangup/>
</Response>"""
    else:
        # Fallback to Twilio's TTS
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{greeting}</Say>
    <Gather input="speech" action="{BASE_URL}/gather" method="POST"
            speechTimeout="auto" language="en-US">
        <Say>I'm listening.</Say>
    </Gather>
    <Say>I didn't hear anything. Goodbye!</Say>
    <Hangup/>
</Response>"""

    return Response(twiml, mimetype="text/xml")


@app.route("/gather", methods=["POST"])
def twilio_gather():
    """
    Handle speech input from Twilio's <Gather>.
    Process through ASR -> LLM -> TTS and respond.
    """
    speech_result = request.form.get("SpeechResult", "")
    call_sid = request.form.get("CallSid", "unknown")

    print(f"[SPEECH INPUT] SID: {call_sid}, Text: {speech_result}")

    if not speech_result:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">I didn't catch that. Could you repeat?</Say>
    <Gather input="speech" action="{BASE_URL}/gather" method="POST"
            speechTimeout="auto" language="en-US"/>
    <Say>Still nothing. Goodbye!</Say>
    <Hangup/>
</Response>"""
        return Response(twiml, mimetype="text/xml")

    # Check for goodbye intent
    goodbye_phrases = ["goodbye", "bye", "hang up", "end call", "that's all"]
    if any(phrase in speech_result.lower() for phrase in goodbye_phrases):
        farewell = "Thank you for calling! Have a great day. Goodbye!"
        audio_url = call_tts(farewell)

        if audio_url:
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Hangup/>
</Response>"""
        else:
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{farewell}</Say>
    <Hangup/>
</Response>"""
        return Response(twiml, mimetype="text/xml")

    # Get AI response
    ai_response = call_llm(speech_result)
    print(f"[AI RESPONSE] {ai_response}")

    # Convert to speech
    audio_url = call_tts(ai_response)

    if audio_url:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Gather input="speech" action="{BASE_URL}/gather" method="POST"
            speechTimeout="auto" language="en-US"/>
    <Say>Are you still there?</Say>
    <Hangup/>
</Response>"""
    else:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{ai_response}</Say>
    <Gather input="speech" action="{BASE_URL}/gather" method="POST"
            speechTimeout="auto" language="en-US"/>
    <Say>Are you still there?</Say>
    <Hangup/>
</Response>"""

    return Response(twiml, mimetype="text/xml")


# =============================================================================
# JAMBONZ ENDPOINTS
# =============================================================================

@app.route("/jambonz", methods=["POST"])
def jambonz_webhook():
    """
    Jambonz webhook - called when a call arrives via Jambonz.
    Returns Jambonz verbs (JSON format).
    """
    payload = request.json or {}
    call_sid = payload.get("call_sid", "unknown")
    from_number = payload.get("from", "unknown")

    print(f"[JAMBONZ CALL] SID: {call_sid}, From: {from_number}")

    # Generate greeting
    greeting = "Hello! I'm your AI assistant. How can I help you today?"
    audio_url = call_tts(greeting)

    response = []

    if audio_url:
        response.append({
            "verb": "play",
            "url": audio_url
        })
    else:
        response.append({
            "verb": "say",
            "text": greeting,
            "synthesizer": {
                "vendor": "google",
                "language": "en-US",
                "voice": "en-US-Wavenet-D"
            }
        })

    # Gather speech input
    response.append({
        "verb": "gather",
        "input": ["speech"],
        "actionHook": f"{BASE_URL}/jambonz-gather",
        "timeout": 10,
        "speechTimeout": "auto",
        "recognizer": {
            "vendor": "google",
            "language": "en-US"
        }
    })

    response.append({
        "verb": "say",
        "text": "I didn't hear anything. Goodbye!"
    })

    response.append({"verb": "hangup"})

    return jsonify(response)


@app.route("/jambonz-gather", methods=["POST"])
def jambonz_gather():
    """Handle speech input from Jambonz gather verb."""
    payload = request.json or {}
    speech = payload.get("speech", {})
    speech_text = speech.get("alternatives", [{}])[0].get("transcript", "")

    print(f"[JAMBONZ SPEECH] Text: {speech_text}")

    if not speech_text:
        return jsonify([
            {"verb": "say", "text": "I didn't catch that. Could you repeat?"},
            {
                "verb": "gather",
                "input": ["speech"],
                "actionHook": f"{BASE_URL}/jambonz-gather",
                "timeout": 10
            },
            {"verb": "hangup"}
        ])

    # Check for goodbye
    goodbye_phrases = ["goodbye", "bye", "hang up", "end call"]
    if any(phrase in speech_text.lower() for phrase in goodbye_phrases):
        farewell = "Thank you for calling! Goodbye!"
        audio_url = call_tts(farewell)

        if audio_url:
            return jsonify([
                {"verb": "play", "url": audio_url},
                {"verb": "hangup"}
            ])
        return jsonify([
            {"verb": "say", "text": farewell},
            {"verb": "hangup"}
        ])

    # Get AI response
    ai_response = call_llm(speech_text)
    audio_url = call_tts(ai_response)

    response = []

    if audio_url:
        response.append({"verb": "play", "url": audio_url})
    else:
        response.append({"verb": "say", "text": ai_response})

    response.append({
        "verb": "gather",
        "input": ["speech"],
        "actionHook": f"{BASE_URL}/jambonz-gather",
        "timeout": 10
    })

    response.append({"verb": "hangup"})

    return jsonify(response)


# =============================================================================
# AUDIO SERVING
# =============================================================================

@app.route("/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """Serve generated audio files."""
    audio_path = AUDIO_DIR / filename
    if audio_path.exists():
        return send_file(audio_path, mimetype="audio/wav")
    return jsonify({"error": "Audio not found"}), 404


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           AI HOTLINE WEBHOOK SERVER                          ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                   ║
║    POST /voice         - Twilio webhook                      ║
║    POST /gather        - Twilio speech handler               ║
║    POST /jambonz       - Jambonz webhook                     ║
║    POST /jambonz-gather- Jambonz speech handler              ║
║    GET  /health        - Health check                        ║
║    GET  /audio/<file>  - Serve audio files                   ║
╠══════════════════════════════════════════════════════════════╣
║  Services:                                                    ║
║    TTS:      {TTS_URL:<40}  ║
║    ASR:      {ASR_URL:<40}  ║
║    LLM:      {LLM_URL:<40}  ║
║    Langflow: {LANGFLOW_URL if LANGFLOW_FLOW_ID else 'Not configured':<40}  ║
╠══════════════════════════════════════════════════════════════╣
║  Running on: http://0.0.0.0:{PORT:<5}                             ║
╚══════════════════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=PORT, debug=False)
