# Backend API image. Works on Hugging Face Spaces (Docker SDK), Render,
# Railway, Fly.io, or any VPS. Needs ~8 GB RAM and ~10 GB disk: the models
# (~7 GB) download on first use into HF_HOME.
#
#   docker build -t understand-kamba-api .
#   docker run -p 7860:7860 -e ALLOWED_ORIGINS=https://your-site.vercel.app understand-kamba-api

FROM python:3.12-slim

# Hugging Face Spaces runs containers as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PORT=7860
WORKDIR /home/user/app

# CPU-only PyTorch first: the default wheel bundles CUDA and is several GB larger.
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user app ./app
COPY --chown=user frontend ./frontend

EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
