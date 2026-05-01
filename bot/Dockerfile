FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash app

# Слой зависимостей: ставим пакет с пустым stub-пакетом moirai_bot,
# чтобы хешлинг-бэкенд смог собрать колесо. Реальный код приходит ниже,
# и кеш этого слоя не инвалидируется при правке исходников.
COPY pyproject.toml ./
RUN mkdir -p moirai_bot \
    && : > moirai_bot/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf moirai_bot

COPY moirai_bot/ ./moirai_bot/

USER app

CMD ["python", "-m", "moirai_bot"]
