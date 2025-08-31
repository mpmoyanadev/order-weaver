from __future__ import annotations

from fastapi import FastAPI, HTTPException

from common.config import get_settings
from common.events import pack_envelope, unpack_envelope
from common.kafka import KafkaConsumerWorker, KafkaProducer
from common.logging import get_logger, setup_logging
from common.metrics import setup_metrics_endpoint
from common.otel import instrument_fastapi, setup_otel
from common.topics import (
    INVENTORY_COMMANDS,
    ORDERS_EVENTS,
    PAYMENTS_COMMANDS,
)

settings = get_settings()

app = FastAPI(title="OrderWeaver - Orchestrator", version="0.1.0")

setup_logging(settings.service_name or "orchestrator-service")
setup_otel(settings.service_name or "orchestrator-service", settings.otel_exporter_otlp_endpoint)
instrument_fastapi(app)
setup_metrics_endpoint(app)

log = get_logger(__name__)

# --- Kafka ---
_producer = KafkaProducer()
_orders_consumer: KafkaConsumerWorker | None = None
_kafka_ready: bool = False


async def _handle_orders_event(data: bytes) -> None:
    """Обработчик событий из топика orders.events.

    На событие OrderCreated отправляем две команды:
    - PaymentAuthorize в payments.commands
    - ReserveInventory в inventory.commands
    """
    env, payload = unpack_envelope(data)
    if env.type != "OrderCreated":
        # игнорируем другие события
        return

    # Ленивая загрузка protobuf‑классов
    from common.proto.orders import orders_pb2
    from common.proto.payments import payments_pb2

    created = orders_pb2.OrderCreated()
    created.ParseFromString(payload)

    # Команда авторизации платежа
    pay_cmd = payments_pb2.PaymentAuthorize(order_id=created.order_id, amount=created.amount)
    pay_envelope = pack_envelope(
        payload=pay_cmd.SerializeToString(),
        event_type="PaymentAuthorize",
        source=settings.service_name or "orchestrator-service",
        correlation_id=env.correlation_id or env.id,
        causation_id=env.id,
        traceparent=env.traceparent,
    )
    await _producer.send(PAYMENTS_COMMANDS, pay_envelope)
    log.info("saga", msg="Отправлена команда PaymentAuthorize", order_id=created.order_id)

    # Команда резервирования склада
    reserve_cmd = orders_pb2.ReserveInventory(order_id=created.order_id)
    inv_envelope = pack_envelope(
        payload=reserve_cmd.SerializeToString(),
        event_type="ReserveInventory",
        source=settings.service_name or "orchestrator-service",
        correlation_id=env.correlation_id or env.id,
        causation_id=env.id,
        traceparent=env.traceparent,
    )
    await _producer.send(INVENTORY_COMMANDS, inv_envelope)
    log.info("saga", msg="Отправлена команда ReserveInventory", order_id=created.order_id)


@app.on_event("startup")
async def _startup() -> None:
    if settings.kafka_disabled:
        log.info("kafka", msg="Kafka отключена переменной окружения")
        global _kafka_ready
        _kafka_ready = True
        return
    await _producer.start()
    global _orders_consumer
    _orders_consumer = KafkaConsumerWorker(
        topic=ORDERS_EVENTS,
        group_id="orchestrator",
        handler=_handle_orders_event,
        auto_offset_reset="earliest",
    )
    await _orders_consumer.start()
    global _kafka_ready
    _kafka_ready = True
    log.info("kafka", msg="Оркестратор подключен к Kafka")


@app.on_event("shutdown")
async def _shutdown() -> None:
    if settings.kafka_disabled:
        return
    if _orders_consumer is not None:
        await _orders_consumer.stop()
    await _producer.stop()
    global _kafka_ready
    _kafka_ready = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name or "orchestrator-service"}


@app.get("/")
async def root() -> dict[str, str]:
    log.info("root", msg="Orchestrator service alive")
    return {"message": "Orchestrator service"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    if settings.kafka_disabled:
        return {"status": "ready", "kafka": "disabled"}
    if not _kafka_ready:
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}
