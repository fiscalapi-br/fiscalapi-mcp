# Dependências instaladas do uv.lock (versões e hashes travados), sem as de desenvolvimento.
FROM python:3.15.0-slim AS dependencias
COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.15.0-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=dependencias /app/.venv /app/.venv
COPY fiscalapi_mcp ./fiscalapi_mcp
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8000
# A porta vem de PORT (o Railway define); sem ela, 8000.
CMD ["python", "-m", "fiscalapi_mcp"]
