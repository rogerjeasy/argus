# Argus backend — the image `make deploy` and CI's deploy job build and push to
# Artifact Registry, then Terraform points the Cloud Run service at.
#
# Two stages so Poetry itself never ships: the builder resolves the locked
# production dependencies into a self-contained virtualenv, and the runtime
# stage copies just that venv plus the application code.

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.3.4 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

# Copied on their own so the dependency layer is only rebuilt when the
# dependency set actually changes, not on every application edit.
COPY pyproject.toml poetry.lock ./

# --only main: no pytest/ruff/httpx in the production image.
# --no-root: pyproject sets package-mode = false, so there is no project
# package to install — only its dependencies.
RUN poetry install --only main --no-root


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 1000 argus

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

USER argus

# Must match modules/cloud_run_service/variables.tf's container_port default.
EXPOSE 8000

# 0.0.0.0, not 127.0.0.1: Cloud Run routes to the container's external
# interface, and a loopback-only bind fails the startup health probe.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
