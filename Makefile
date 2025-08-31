.PHONY: up down logs build lint format mypy test gen-protos

up:
	docker compose up -d --build
	docker compose ps

e2e:
	# Полный e2e сценарий: пересобрать, поднять стек, проверить health, отправить заказ, показать логи
	-docker compose down -v
	docker compose up -d --build
	# ждём, пока поднимутся redpanda и сервисы
	sleep 25
	# health
	curl -sS http://localhost:8001/health
	curl -sS http://localhost:8002/health
	curl -sS http://localhost:8003/health
	curl -sS http://localhost:8004/health
	# создаём заказ
	curl -sS -X POST http://localhost:8001/orders -H 'Content-Type: application/json' -d '{"order_id":"o-1","user_id":"u-1","amount":123.45}'
	# ключевые логи
	-@docker logs orchestrator --since=2m --tail=200
	-@docker logs payments --since=2m --tail=200
	-@docker logs inventory --since=2m --tail=200

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

build:
	docker compose build --no-cache

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check --fix .

mypy:
	mypy .

test:
	pytest -q

gen-protos:
	bash scripts/gen_protos.sh
