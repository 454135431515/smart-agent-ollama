# Stage 1 — install dependencies into an isolated venv
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# Stage 2 — minimal runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy venv from builder (no build tools in the final image)
COPY --from=builder /opt/venv /opt/venv

# Copy only application source
COPY app/     app/
COPY tools/   tools/
COPY main.py  .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]
