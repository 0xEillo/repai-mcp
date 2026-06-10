FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first for layer caching
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Audit log persists here; mount a volume to keep it across runs
ENV REPAI_MCP_AUDIT_PATH=/data/audit.jsonl
RUN mkdir -p /data

# stdio transport: run with `docker run -i --env-file .env repai-mcp`
ENTRYPOINT ["uv", "run", "--no-sync", "repai-mcp"]
