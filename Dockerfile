# XTTS-v2 TTS Server for RunPod
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY tts_server.py .
COPY download_model.py .

# Download the XTTS-v2 model during build
RUN python download_model.py

# Create samples directory
RUN mkdir -p samples

# Expose the port
EXPOSE 5000

# Set environment variables
ENV PORT=5000
ENV OLLAMA_URL=http://host.docker.internal:11434
ENV LLM_MODEL=llama3.1:8b

# Run the server
CMD ["python", "tts_server.py"]
