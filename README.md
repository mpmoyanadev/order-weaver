# OrderWeaver — event-driven e‑commerce ядро на сагах

Проект демонстрирует распределённые транзакции через паттерн саг (orchestration), обмен событиями между микросервисами `orders`, `payments`, `inventory` и отдельным сервисом‑оркестратором `orchestrator`. Используются FastAPI, Kafka/Redpanda, Postgres, Protobuf, SQLAlchemy/Alembic, OpenTelemetry.

## Архитектура (высокоуровнево)
- Микросервисы: `orders`, `payments`, `inventory`, `orchestrator`.
- События в Kafka/Redpanda; контракты в `proto/` (Protobuf).
- Саги: базово orchestration (сервис `orchestrator`), хореография — в roadmap.
- Паттерны: outbox/inbox, транзакционные сообщения, дедлеттеры, идемпотентность, реплеи.
- Наблюдаемость: OpenTelemetry (OTLP → Jaeger), структурные логи, метрики Prometheus.

Диаграммы и подробности см. в `docs/` (будут дополняться).

## Быстрый старт (Docker)
Требования: Docker Desktop, Docker Compose.

```bash
# запустить инфраструктуру и сервисы
docker compose up -d --build

# логи всего стека
docker compose logs -f

# остановить
docker compose down -v
```

Порты по умолчанию:
- Orders: http://localhost:8001/docs
- Payments: http://localhost:8002/docs
- Inventory: http://localhost:8003/docs
- Orchestrator: http://localhost:8004/docs
- Redpanda Console: http://localhost:8081
- Jaeger UI: http://localhost:16686

Проверка:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

Готовность к Kafka (readiness):
```bash
curl http://localhost:8001/ready
curl http://localhost:8002/ready
curl http://localhost:8003/ready
curl http://localhost:8004/ready
```

## E2E за один заход
Удобный сценарий целиком — билд, запуск, health‑чеки, POST заказа и логи:

```
make e2e
```

Альтернатива без make:
```
docker compose down -v
docker compose up -d --build
sleep 25
curl -sS http://localhost:8001/health
curl -sS http://localhost:8002/health
curl -sS http://localhost:8003/health
curl -sS http://localhost:8004/health
curl -sS -X POST http://localhost:8001/orders -H 'Content-Type: application/json' -d '{"order_id":"o-1","user_id":"u-1","amount":123.45}'
docker logs orchestrator --since=2m --tail=200
docker logs payments --since=2m --tail=200
docker logs inventory --since=2m --tail=200
```

### Windows: единый скрипт локальной проверки

Для быстрой локальной проверки (venv, зависимости, генерация прото, ruff/black/mypy, pytest и Docker E2E) используйте PowerShell‑скрипт:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev_full_check.ps1
```

## Локальный запуск сервиса (без Docker)
```bash
python -m venv .venv && source .venv/bin/activate  # Win: .venv\\Scripts\\activate
pip install -r requirements/dev.txt
pip install -r requirements/common.txt
uvicorn services.orders.app.main:app --reload --port 8001
```
Переменные окружения см. в `.env.example` (OTEL, Kafka, БД).

## Прото‑контракты
Исходники в `proto/`. Генерация Python‑кода в `common/proto/`:
```bash
make gen-protos
# или
./scripts/gen_protos.sh
# на Windows также есть PowerShell‑скрипт
pwsh -File scripts/gen_protos.ps1
```

## Миграции БД (Alembic)
Для каждого сервиса своя схема миграций (папка `services/<svc>/alembic/`). Пример команд:
```bash
# пример для orders
alembic -c services/orders/alembic.ini revision -m "init"
alembic -c services/orders/alembic.ini upgrade head
```

## Тесты и качество
```bash
make lint   # ruff + black --check
make mypy
make test
```
CI: GitHub Actions (`.github/workflows/ci.yml`). Pre-commit — `.pre-commit-config.yaml`.

## Observability
- OTEL экспорт: OTLP HTTP → Jaeger (4318). См. `common/otel.py` и переменные окружения `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`.
- Метрики: `/metrics` в каждом сервисе (Prometheus формат).

## Безопасность
- Валидация входа (FastAPI + pydantic).
- Rate limit, идемпотентность, защита секретов — в планах; базовые заготовки будут добавлены.
- Статический анализ: ruff, mypy, bandit, pip‑audit (через pre‑commit/CI).

## ADR и roadmap
- ADR‑заметки: `docs/adr/ADR-0001-architecture.md`.
- Roadmap: `docs/ROADMAP.md`.

## Лицензия
MIT (можно изменить).
