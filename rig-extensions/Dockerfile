FROM llmrig-elpis:20261029
USER root
COPY uv /usr/local/bin/uv
ENV UV_HTTP_TIMEOUT=600 UV_CONCURRENT_DOWNLOADS=2
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/venv/bin/python faster-whisper==1.2.1 pymupdf pillow
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/venv/bin/python --target /opt/asr-libs nvidia-cublas-cu12 nvidia-cudnn-cu12
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/venv/bin/python --no-deps --index-url https://download.pytorch.org/whl/cu130 torchvision==0.25.0
RUN --mount=type=cache,target=/root/.cache/uv uv pip install --python /opt/venv/bin/python av==16.1.0
COPY worker.py /opt/rig/worker.py
ENV HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
USER 1000:1000
ENTRYPOINT ["/opt/venv/bin/python", "-B", "/opt/rig/worker.py"]
