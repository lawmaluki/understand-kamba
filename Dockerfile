# Backend API image for hosts other than the Hugging Face Space (e.g. Render,
# Railway, Fly.io or a VPS). Needs ~6 GB RAM and ~8 GB disk; the models
# download on first use into HF_HOME. The live backend runs on the Hugging
# Face Space instead (space/ + scripts/deploy_space.py).
#
# This image runs everything on CPU: translation (NLLB_MODEL_ID), speech-to-
# text, and the Swahili MMS voice. The GPU models (NLLB-3.3B, OmniVoice Kamba
# voice) are wired up only in space/server.py, for ZeroGPU.
#
#   docker build -t understand-kamba-api .
#   docker run -p 7860:7860 understand-kamba-api

FROM python:3.12-slim

# Hugging Face Spaces (and many hosts) run containers as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    DISABLE_SAFETENSORS_CONVERSION=1 \
    PORT=7860
WORKDIR /home/user/app

# CPU-only PyTorch first: the default wheel bundles CUDA and is several GB larger.
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user app ./app

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
