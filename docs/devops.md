# bioeq_ai

## Локальный запуск через Docker Compose

1. Скопируйте шаблон переменных окружения:

```bash
cp .env.example .env
```

2. Поднимите стек:

```bash
docker compose up -d --build
```

3. Проверьте health endpoint:

```bash
curl http://localhost:8000/health
```

## Запуск тестов в venv

1. Создайте и активируйте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Установите зависимости проекта и `pytest`:

```bash
pip install -r requirements.txt pytest
```

3. Запустите тесты:

```bash
pytest -q
```

4. Если нужны только юнит-тесты:

```bash
pytest -q tests/unit
```

5. Для `tests/on_wake_up` контейнеры должны быть подняты и доступны на localhost (`8000`, `6379`, `5432`, `9000`, `6333`):

```bash
docker compose up -d --build
pytest -q tests/on_wake_up
```

## Сервисы в docker-compose

- `app` (приложение из `main.py` на FastAPI + uvicorn)
- `redis` (порт `6379`)
- `postgres` (порт `5432`)
- `minio` (порты `9000`, `9001`)
- `qdrant` (порты `6333`, `6334`)

## GitHub Actions CI/CD

Workflow: `.github/workflows/deploy.yml`

Что делает при пуше в `main`:

1. Собирает Docker-образ из репозитория.
2. Публикует образ в GHCR (`ghcr.io/<owner>/bioeq-ai:latest`).
3. Подключается к серверу по SSH и обновляет контейнер `app`.

Необходимые secrets в репозитории:

- `SERVER_HOST` - IP/домен сервера
- `SERVER_USER` - SSH-пользователь
- `SERVER_SSH_KEY` - приватный SSH-ключ
- `SERVER_PORT` - опционально, по умолчанию `22`
- `DEPLOY_PATH` - абсолютный путь к проекту на сервере (пример: `/opt/bioeq_ai`)
- `GHCR_USERNAME` - пользователь GitHub с доступом к пакетам
- `GHCR_TOKEN` - токен GitHub с правом `read:packages` (для pull образа на сервере)

## Деплой

Деплой выполняется только через GitHub Actions (`.github/workflows/deploy.yml`) при пуше в ветку `main` или при ручном запуске workflow из GitHub UI.