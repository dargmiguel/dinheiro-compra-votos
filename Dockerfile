FROM python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d

COPY --from=ghcr.io/astral-sh/uv:0.9.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project \
    && mkdir -p /app/reports /app/data/raw /app/data/derived

COPY tse_pilot/ ./tse_pilot/
COPY tests/ ./tests/
COPY data/manifests/ ./data/manifests/
COPY data/inventory-2022.json data/layout-2022.json ./data/

ENV PATH="/opt/venv/bin:${PATH}"

ENTRYPOINT ["uv", "run", "--locked", "--no-sync", "python", "-m", "tse_pilot"]
CMD ["--help"]
