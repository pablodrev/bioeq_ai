# MedDesign MVP - Backend Developer Guide

## Overview

Полный backend на FastAPI для автоматизации проектирования исследований биоэквивалентности. За 48 часов разработано:

### Модуль 1: Поиск и экстракция параметров ✅
- **PubMed интеграция** (`services/pubmed.py`): поиск статей по МНН
- **YandexGPT клиент** (`services/llm_client.py`): экстракция Cmax, AUC, T1/2, Tmax, CV_intra
- **Parsing module** (`core/parsing_module.py`): оркестрация поиска и сохранение в БД

### Модуль 2: Расчет параметров исследования ✅
- **Calculator** (`services/calculator.py`): формула для расчета размера выборки (2x2 crossover)
- **Design module** (`core/design_module.py`): генерация дизайна исследования

### Модуль 3: Регуляторная проверка ✅
- **Regulatory module** (`core/regulatory_module.py`): быстрая проверка соответствия требованиям ЕАЭС

### Модуль 4: Генерация отчета ✅
- **Report module** (`core/report_module.py`): создание синопсиса в формате DOCX

---

## Структура проекта

```
backend/
├── main.py                    # FastAPI приложение (все эндпоинты)
├── database.py               # SQLAlchemy + PostgreSQL
├── models.py                 # DBProject, DBDrugParameter
├── schemas.py                # Pydantic валидация
├── requirements.txt          # Зависимости
├── .env                      # Конфиг (API ключи)
├── reports/                  # Сгенерированные DOCX файлы
├── services/
│   ├── pubmed.py            # PubMed E-Utilities клиент
│   ├── llm_client.py        # YandexGPT API клиент
│   └── calculator.py        # Формулы расчетов
└── core/
    ├── parsing_module.py    # Оркестрация поиска
    ├── design_module.py     # Генерация дизайна
    ├── regulatory_module.py # Регуляторная проверка
    └── report_module.py     # Генерация DOCX
```

---

## API Endpoints

### 1. Запуск поиска (асинхронно)
```bash
POST /api/v1/search/start
Content-Type: application/json

{
  "inn_en": "Ibuprofen",
  "inn_ru": "Ибупрофен",
  "dosage": "400mg",
  "form": "tablets"
}

# Ответ:
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "searching",
  "message": "..."
}
```

### 2. Получить результаты
```bash
GET /api/v1/search/results/{project_id}

# Ответ:
{
  "project_id": "550e8400-...",
  "status": "completed",
  "parameters": [
    {
      "parameter": "CV_intra",
      "value": "22.5",
      "unit": "%",
      "source": "PubMed ID: 3456789",
      "is_reliable": true
    }
  ],
  "sources_count": 3
}
```

### 3. Получить все детали проекта
```bash
GET /api/v1/projects/{project_id}

# Ответ включает:
# - Информацию о препарате
# - Найденные параметры
# - Дизайн исследования (sample_size, CV, washout период)
# - Статус регуляторной проверки (compliant/rejected)
```

### 4. Сгенерировать отчет (DOCX)
```bash
POST /api/v1/reports/{project_id}/generate
```

### 5. Скачать отчет
```bash
GET /api/v1/reports/{project_id}/download
```

---

## Установка и запуск

### Требования
- Python 3.10+
- PostgreSQL (локально или в Docker)
- API ключи: YandexGPT (Yandex.Cloud)

### 1. Настройка БД
```bash
# Локально (Windows):
# 1. Установить PostgreSQL
# 2. Создать БД:
createdb pharma_mvp

# Или в Docker:
docker run --name pharma-db -e POSTGRES_PASSWORD=pharma_password \
  -e POSTGRES_DB=pharma_mvp -p 5432:5432 -d postgres:15
```

### 2. Установка зависимостей
```bash
pip install -r backend/requirements.txt
```

### 3. Настройка .env
```bash
cat > backend/.env << EOF
DATABASE_URL=postgresql://pharma_user:pharma_password@localhost:5432/pharma_mvp
YANDEX_GPT_API_KEY=your_key_here
YANDEX_FOLDER_ID=your_folder_id_here
DEBUG=True
EOF
```

### 4. Запуск сервера
```bash
cd backend
python main.py

# Или с uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Проверка
```bash
curl http://localhost:8000/api/v1/health

# Ответ: {"status": "healthy", "timestamp": "2025-02-21T..."}
```

---

## Поток выполнения (Workflow)

```
POST /search/start
    ↓
[Background Task 1] Поиск в PubMed
    ↓
[Background Task 2] Экстракция параметров (LLM)
    ↓
[Background Task 3] Генерация дизайна (расчет N)
    ↓
[Background Task 4] Регуляторная проверка
    ↓
[Background Task 5] Генерация DOCX
    ↓
GET /projects/{id} → Download /reports/{id}/download
```

**Статусы проекта:**
- `searching` → `searching_completed` → `completed`
- Или: `search_failed`, `design_failed`, `regulatory_check_failed`, `failed`

---

## Примеры использования

### Пример 1: Полный цикл (cURL)
```bash
# 1. Запуск поиска
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/v1/search/start \
  -H "Content-Type: application/json" \
  -d '{"inn_en":"Ibuprofen","dosage":"400mg","form":"tablets"}' | jq -r '.project_id')

# 2. Проверить статус (с интервалом в 5 сек)
for i in {1..30}; do
  curl -s http://localhost:8000/api/v1/projects/$PROJECT_ID | jq '.status'
  sleep 5
done

# 3. Скачать отчет
curl -X GET http://localhost:8000/api/v1/reports/$PROJECT_ID/download \
  -o ibuprofen_report.docx
```

### Пример 2: Python клиент
```python
import httpx
import json
import time

client = httpx.Client(base_url="http://localhost:8000")

# Start search
resp = client.post("/api/v1/search/start", json={
    "inn_en": "Ibuprofen",
    "dosage": "400mg",
    "form": "tablets"
})
project_id = resp.json()["project_id"]
print(f"Started: {project_id}")

# Poll results
while True:
    project = client.get(f"/api/v1/projects/{project_id}").json()
    print(f"Status: {project['status']}")
    
    if project['status'] == "completed":
        print(f"Sample size: {project['design_parameters']['sample_size']}")
        print(f"CV_intra: {project['design_parameters']['critical_parameters']['CV_intra']}%")
        break
    
    time.sleep(5)

# Download report
with open("report.docx", "wb") as f:
    f.write(client.get(f"/api/v1/reports/{project_id}/download").content)
```

---

## Ключевые особенности MVP

1. **Быстрый старт:** FastAPI BackgroundTasks вместо Celery
2. **JSONB в БД:** Вся динамика (параметры, дизайн, проверка) → JSON
3. **Async API:** Не блокирует при поиске в PubMed и вызовах LLM
4. **Готовые DOCX:** Используется python-docx, поддерживает таблицы и форматирование
5. **Регулярные проверки:** Встроенная валидация по стандартам ЕАЭС

---

## Что дальше (не в MVP)

- [ ] Фронтенд (React Wizard)
- [ ] Docker-файл и docker-compose
- [ ] CI/CD (GitHub Actions)
- [ ] Более сложный RAG (Qdrant + embeddings)
- [ ] Расширенная регуляторная логика
- [ ] Кэширование результатов PubMed
- [ ] Логирование в ElasticSearch

---

## Отладка

### Включить подробное логирование
```python
# В main.py строка 30
logging.basicConfig(
    level=logging.DEBUG,  # вместо INFO
    ...
)
```

### Проверить БД
```bash
psql -U pharma_user -d pharma_mvp

# SQL команды:
SELECT * FROM projects;
SELECT * FROM drug_parameters WHERE project_id = '...';
```

### Проверить LLM отклик
```python
from services.llm_client import YandexGPTClient

llm = YandexGPTClient(api_key="...", folder_id="...")
result = llm.extract_parameters("Some abstract text", "Ibuprofen")
print(result)
```

---

## Контакты / Контрольная точка

✅ **48-часовой дедлайн пройден:**

1. ✅ PubMed интеграция (поиск + fetch abstracts)
2. ✅ YandexGPT экстракция параметров
3. ✅ Расчет sample size (2x2 crossover)
4. ✅ Регуляторная проверка
5. ✅ Генерация DOCX синопсиса
6. ✅ Полный FastAPI с Background Tasks

**Готово к использованию!**
