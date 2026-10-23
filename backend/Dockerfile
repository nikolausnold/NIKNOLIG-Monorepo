FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 backend \
    && useradd --uid 10001 --gid 10001 --no-create-home backend
COPY asgi.py database.py migrate.py deployment.py healthcheck.py ai_support.py support_http.py workers_ai.py ./
COPY migrations ./migrations
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=6s --start-period=10s --retries=3 \
    CMD ["python", "healthcheck.py"]
CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-server-header", "--no-access-log", "--limit-concurrency", "64", "--timeout-keep-alive", "5"]
