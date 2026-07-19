FROM python:3.12-slim

# ffmpeg  — decodes the browser's webm/opus answers for Whisper
# libportaudio2 — import-time requirement of sounddevice (desktop path, showcase.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

RUN useradd --create-home --uid 1000 app && chown app:app /app
USER app

COPY --chown=app:app requirments.txt .
RUN pip install --no-warn-script-location -r requirments.txt

# Bake the Whisper "base" weights into the image so the first interview
# doesn't stall on a ~150MB download. Must run as `app` so the cache
# lands in a directory the runtime user can read.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

COPY --chown=app:app . .

# Single process: Flask serves the API, the Socket.IO endpoint, and the
# static UI in ui/ (see src/api/app.py) — one port, not two.
ENV HOST=0.0.0.0 \
    PORT=4567 \
    DEBUG=0

EXPOSE 4567

CMD ["python", "run.py"]
