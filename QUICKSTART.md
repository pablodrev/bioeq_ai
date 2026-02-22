# 🚀 БЫСТРЫЙ СТАРТ - MedDesign MVP Backend

Полный backend приложение для автоматизации проектирования исследований биоэквивалентности разработано за 48 часов.

---

## 📦 Что включено

### Файлы конфигурации

- `requirements.txt` - все зависимости
- `.env` - конфиг (нужны YandexGPT ключи)
- `README_BACKEND.md` - полная документация

### Core приложение

- `main.py` - FastAPI со всеми эндпоинтами (395 строк)
- `database.py` - PostgreSQL подключение
- `models.py` - DBProject, DBDrugParameter
- `schemas.py` - Pydantic валидация

### Сервисы (интеграции)

- `services/pubmed.py` - поиск в PubMed (E-Utilities API)
- `services/llm_client.py` - YandexGPT для экстракции параметров
- `services/calculator.py` - БЭ расчеты (sample size, washout)

### Бизнес-логика (core/)

- `core/parsing_module.py` - оркестрация PubMed + LLM
- `core/design_module.py` - генерация дизайна исследования
- `core/regulatory_module.py` - регуляторная проверка
- `core/report_module.py` - генерация DOCX

### Тестирование

- `test_integration.py` - проверка всех импортов и функций

---

## ⚡ 5-минутный старт

### 1. Установка зависимостей

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Установить пакеты:
pip install -r requirements.txt
```

### 2. Настроить .env

```bash
# Отредактировать backend/.env
DATABASE_URL=postgresql://user:password@localhost:5432/pharma_mvp
YANDEX_GPT_API_KEY=your_key   # Получить в Yandex.Cloud
YANDEX_FOLDER_ID=your_id      # ID папки в Yandex.Cloud
```

### 3. Поднять БД (PostgreSQL)

```bash
# Docker (рекомендуется):
docker run --name pharma-db -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=pharma_mvp -p 5432:5432 -d postgres:15

# Или локально (Windows):
# Установить PostgreSQL, создать БД pharma_mvp
```

### 4. Запустить сервер

```bash
cd backend
python main.py

# Или:
uvicorn main:app --reload --port 8000
```

Сервер запустится на `http://localhost:8000`

### 5. Тестировать

```bash
# Открыть Swagger UI:
http://localhost:8000/docs

# Или через cURL:
curl http://localhost:8000/api/v1/health

# Стартовать поиск:
curl -X POST http://localhost:8000/api/v1/search/start \
  -H "Content-Type: application/json" \
  -d '{
    "inn_en": "Ibuprofen",
    "dosage": "400mg",
    "form": "tablets"
  }'
```

---

## 🔄 Основной workflow

```
1. POST /api/v1/search/start
   └─ Получить project_id

2. Background tasks (параллельно):
   ├─ Поиск в PubMed
   ├─ Экстракция параметров (LLM)
   ├─ Генерация дизайна
   ├─ Регуляторная проверка
   └─ Генерация DOCX

3. GET /api/v1/projects/{id}
   └─ Смотреть статус и результаты

4. GET /api/v1/reports/{id}/download
   └─ Скачать готовый Word
```

---

## 📊 Полный API

| Метод | Путь                            | Описание           |
| ----- | ------------------------------- | ------------------ |
| GET   | `/api/v1/health`                | Проверка статуса   |
| POST  | `/api/v1/search/start`          | Запуск поиска      |
| GET   | `/api/v1/search/results/{id}`   | Результаты поиска  |
| GET   | `/api/v1/projects/{id}`         | Все детали проекта |
| POST  | `/api/v1/reports/{id}/generate` | Генерация DOCX     |
| GET   | `/api/v1/reports/{id}/download` | Скачать DOCX       |

---

## 📋 Что работает (MVP)

✅ Поиск в PubMed (E-Utilities API)  
✅ Экстракция ФК параметров через YandexGPT  
✅ Расчет sample size (2x2 crossover design)  
✅ Определение washout периода  
✅ Регуляторная проверка (ЕАЭС)  
✅ Генерация синопсиса в DOCX  
✅ Background задачи (async выполнение)  
✅ Логирование всех этапов  
✅ REST API с Swagger UI  
✅ PostgreSQL с SQLAlchemy

---

## 🛠️ Известные ограничения

- ❌ Нет фронтенда (используй Swagger или cURL)
- ❌ Нет Docker файла (но код готов к контейнеризации)
- ❌ Нет аутентификации (открытый API)
- ❌ Нет кэширования PubMed результатов
- ❌ Упрощённая регуляторная логика

---

## 📚 Коды статусов проекта

| Статус                    | Описание                        |
| ------------------------- | ------------------------------- |
| `searching`               | Идёт поиск параметров           |
| `searching_completed`     | Параметры собраны               |
| `completed`               | Всё готово (дизайн + регулярка) |
| `search_failed`           | Ошибка при поиске в PubMed      |
| `design_failed`           | Ошибка при генерации дизайна    |
| `regulatory_check_failed` | Ошибка при проверке             |
| `failed`                  | Общая ошибка                    |

---

## 💡 Примеры использования

### Python

```python
import httpx
import time

client = httpx.Client(base_url="http://localhost:8000")

# Запустить поиск
resp = client.post("/api/v1/search/start", json={
    "inn_en": "Paracetamol",
    "dosage": "500mg",
    "form": "tablets"
})
project_id = resp.json()["project_id"]

# Ждём завершения
while True:
    project = client.get(f"/api/v1/projects/{project_id}").json()
    print(f"Status: {project['status']}")

    if project["status"] == "completed":
        print(f"✓ Sample size: {project['design_parameters']['sample_size']}")
        print(f"✓ CV_intra: {project['design_parameters']['critical_parameters']['CV_intra']}%")
        break

    time.sleep(5)

# Скачать отчет
report = client.get(f"/api/v1/reports/{project_id}/download")
with open("report.docx", "wb") as f:
    f.write(report.content)
```

### Bash

```bash
#!/bin/bash

# Start search
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/search/start \
  -H "Content-Type: application/json" \
  -d '{
    "inn_en": "Ibuprofen",
    "dosage": "400mg",
    "form": "tablets"
  }')

PROJECT_ID=$(echo $RESPONSE | jq -r '.project_id')
echo "Started: $PROJECT_ID"

# Poll status
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/projects/$PROJECT_ID | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    break
  fi

  sleep 5
done

# Download
curl http://localhost:8000/api/v1/reports/$PROJECT_ID/download \
  -o report.docx

echo "✓ Report saved: report.docx"
```

---

## 🧪 Проверка синтаксиса

Все файлы проверены на синтаксис:

```bash
python -m py_compile main.py models.py schemas.py database.py \
  services/*.py core/*.py
```

✅ Ошибок не найдено

---

## 📞 Support

Если что-то не работает:

1. Проверь `.env` файл (YandexGPT ключи)
2. Убедись, что PostgreSQL запущена
3. Смотри логи в консоли сервера
4. Проверь Swagger API: http://localhost:8000/docs

---

## 🎯 Следующие шаги

1. **Развернуть на продакшене:**
   - Dockerfile + docker-compose
   - Nginx reverse proxy
   - SSL сертификат

2. **Фронтенд:**
   - React приложение
   - Wizard (4 шага)
   - Интеграция с API

3. **Оптимизация:**
   - Кэширование PubMed
   - Background job queue (Celery)
   - Database индексы

---

**Разработано за 48 часов**  
**Готово к использованию** ✅
