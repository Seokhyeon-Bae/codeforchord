FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    vamp-plugin-sdk \
    && rm -rf /var/lib/apt/lists/*

# Download and install Chordino VAMP plugin
RUN mkdir -p /usr/local/lib/vamp \
    && cd /tmp \
    && apt-get update && apt-get install -y wget \
    && wget https://code.soundsoftware.ac.uk/attachments/download/2625/nnls-chroma-linux64-v1.1.tar.bz2 \
    && tar -xjf nnls-chroma-linux64-v1.1.tar.bz2 \
    && cp nnls-chroma-linux64-v1.1/*.so /usr/local/lib/vamp/ \
    && rm -rf /tmp/* \
    && apt-get remove -y wget && apt-get autoremove -y

# Set VAMP plugin path
ENV VAMP_PATH=/usr/local/lib/vamp

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory
RUN mkdir -p /app/temp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
