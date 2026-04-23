FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости по минимуму
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Зависимости устанавливаем отдельным слоем для кешируемости
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install .

# State-каталог маунтим снаружи (docker-compose volume)
RUN mkdir -p /app/state

CMD ["python", "-m", "src.main"]
