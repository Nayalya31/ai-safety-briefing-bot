# ИИ-ассистент по инструктажу безопасности

Русскоязычный Telegram-бот для короткого обучения по материалам работодателя и проверки понимания. Репозиторий содержит только вымышленный материал с явной пометкой «Демо».

> Бот предназначен для обучения и самопроверки. Он не заменяет официальный инструктаж, допуск к работе, экстренные службы и утверждённые процедуры работодателя.

## Сценарий

`/start` → открытие демоматериала → короткое обучение и вопросы к материалу → проверяемые вопросы по одному → итог → запись результата в PostgreSQL.

Прогресс хранится в PostgreSQL и восстанавливается после перезапуска. Каждый Telegram `update_id` фиксируется в отдельной таблице, а результат имеет уникальность по учебной сессии, поэтому повторная обработка не создаёт дубль.

Команды: `/start`, `/help`, `/cancel`.

## Архитектура

- `app/bot` — обработчики Telegram, клавиатуры и транзакционная дедупликация обновлений;
- `app/services/training.py` — порядок этапов, проверка вариантов и подсчёт;
- `app/services/ai_explainer.py` — Responses API и строгая JSON Schema;
- `app/db` — SQLAlchemy async, модели и репозиторий;
- `materials` — версионируемые материалы и вопросы;
- `migrations` — Alembic;
- `tests` — unit- и PostgreSQL-интеграционные тесты.

Модель не решает, сколько будет вопросов, не выставляет балл и не меняет правильные ответы. Она объясняет материал и ошибки. В модель не отправляются Telegram ID, имена или результаты сотрудников.

## Безопасная конфигурация

Скопируйте `.env.example` в `.env` и заполните значения. Не коммитьте `.env`.

```env
BOT_TOKEN=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
DATABASE_URL=postgresql+asyncpg://...
```

Для реальных материалов сначала получите утверждённую работодателем версию, оцените конфиденциальность и только затем добавляйте отдельный версионируемый файл. Демо не должно использоваться как рабочая инструкция.

Безопасная read-only проверка Telegram webhook и совместимости Responses API:

```bash
.venv/bin/python -m scripts.check_integrations
```

Скрипт выводит только статусы `yes/no`, без токенов, имён и идентификаторов.

## Запуск Docker Compose

```bash
cp .env.example .env
# заполните секреты и задайте POSTGRES_PASSWORD в окружении хоста
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 bot
```

База доступна только во внутренней сети Compose. Перед запуском бот выполняет `alembic upgrade head`. Проверки контейнера: `python -m app.ready`, HTTP `/healthz` и `/readyz` внутри сети.

## Локальные тесты

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Для интеграционной проверки с отдельной PostgreSQL:

```bash
docker compose -f docker-compose.test.yml up -d --wait
TEST_DATABASE_URL=postgresql+asyncpg://safety_test:safety_test@127.0.0.1:55432/safety_test .venv/bin/pytest tests/test_repository.py
docker compose -f docker-compose.test.yml down
```

## Перед публикацией

1. Убедитесь, что `git status` не содержит `.env`.
2. Выполните `.venv/bin/python -m scripts.secret_scan`; сканер не печатает найденное значение.
3. Проверьте рабочее дерево и историю на реальные инструкции и персональные данные.
4. Публикуйте только демоматериал и код, права на которые подтверждены.
5. До контрольного Telegram-запуска проверьте `getWebhookInfo` и отсутствие другого polling-экземпляра.
