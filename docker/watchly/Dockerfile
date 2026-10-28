# syntax=docker/dockerfile:1
# Watchly with self-hosted Nuvio backend support.
#
# Builds the unmodified upstream source (pinned via WATCHLY_REF) and layers an
# entrypoint on top that rewrites the hard-coded Nuvio cloud endpoint at
# container start, driven entirely by environment variables. See entrypoint.sh.
#
# Used by the anyumbrelstore-watchly Umbrel app.

ARG WATCHLY_REF=1.17.2

FROM python:3.12-slim AS source
ARG WATCHLY_REF
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch "${WATCHLY_REF}" https://github.com/TimilsinaBimal/Watchly.git .

FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"
COPY --from=source /src/app/ ./app/
COPY --from=source /src/main.py .
COPY --from=source /src/CHANGELOG.md .
COPY --from=source /src/pyproject.toml .
COPY --from=source /src/uv.lock .
RUN uv sync --locked
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
