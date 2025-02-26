FROM python:3.11-alpine as builder

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3
RUN apk add --no-cache alpine-sdk linux-headers
RUN pip install poetry

WORKDIR /app

# Install split into two steps (the dependencies and the sources)
# in order to leverage the Docker caching
COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --no-interaction --no-ansi --no-cache --no-root --no-directory --only main

COPY . .
RUN poetry install --no-interaction --no-ansi --no-cache --only main

FROM python:3.11-alpine as server

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3
# fix CVE-2023-52425
RUN apk upgrade --no-cache libexpat
# fix CVE-2024-6345
RUN pip install "setuptools==70.0.0"

WORKDIR /app

# Copy the sources and virtual env. No poetry.
RUN adduser -u 1001 --disabled-password --gecos "" appuser
COPY --chown=appuser --from=builder /app .

COPY ./scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x /docker_entrypoint.sh

ENV LOG_LEVEL=INFO
EXPOSE 5000

USER appuser
ENTRYPOINT ["/docker_entrypoint.sh"]

CMD ["uvicorn", "aidial_adapter_bedrock.app:app", "--host", "0.0.0.0", "--port", "5000"]
