FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for audio DSP (libsndfile) and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

COPY . .

# Generate demo audio fixtures if missing
RUN python scripts/make_demo_fixtures.py

# Create database and assets directories
RUN mkdir -p data assets/models

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV VOICESHIELD_HOST=0.0.0.0
ENV VOICESHIELD_PORT=8000

CMD ["python", "-m", "voiceshield", "all-in-one"]
