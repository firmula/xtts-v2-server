# Hotline Webhook Server Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask flask-cors requests

# Copy server code
COPY hotline_server.py .

# Create audio cache directory
RUN mkdir -p /app/audio_cache

# Expose port
EXPOSE 8080

# Run server
CMD ["python", "hotline_server.py"]
