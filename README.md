# Async Task Service

Сервис асинхронного выполнения задач.

`POST /api/v1/tasks` сохраняет задачу и событие outbox в одной транзакции PostgreSQL. Отдельный outbox-worker публикует событие в приоритетную очередь RabbitMQ. Consumer можно масштабировать репликами; он переводит задачу в `IN_PROGRESS`, выполняет её и сохраняет `COMPLETED` с результатом или `FAILED` с ошибкой.

Доставка сообщений работает по принципу at-least-once. Consumer идемпотентен: уже завершённую либо отменённую задачу он повторно не выполняет.

## Запуск

```bash
copy .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Документация API: http://localhost:8000/docs  
RabbitMQ UI: http://localhost:15672 (`guest`/`guest`)

Для масштабирования consumer:
```bash
docker compose up --scale consumer=3
```

Создание:
```bash
curl -X POST http://localhost:8000/api/v1/tasks ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Generate report\",\"description\":\"Daily report\",\"priority\":\"HIGH\"}"
```

Список задач:
```bash
curl "http://localhost:8000/api/v1/tasks?status=PENDING&priority=HIGH&page=1&page_size=20"
```

Получение задачи:
```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

Получение статуса задачи:
```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}/status"
```

Отмена задачи:
```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/{task_id}"
```

Отмена разрешена только в `NEW` и `PENDING`. Для выполняющейся задачи сервис возвращает `409 Conflict`.

## Тесты

```bash
uv run pytest
```

Интеграционные тесты требуют поднятых PostgreSQL и RabbitMQ и запускаются явно:
```bash
RUN_INTEGRATION=1 uv run pytest -m integration
```
