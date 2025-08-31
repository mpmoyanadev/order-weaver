from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.config import get_settings
from common.events import pack_envelope
from common.kafka import KafkaProducer
from common.logging import get_logger, setup_logging
from common.metrics import setup_metrics_endpoint
from common.otel import instrument_fastapi, setup_otel
from common.topics import ORDERS_EVENTS

# Прото‑классы импортируем лениво внутри обработчика, чтобы тесты без прото не падали

settings = get_settings()

app = FastAPI(title="OrderWeaver - Orders", version="0.1.0")

setup_logging(settings.service_name or "orders-service")
setup_otel(settings.service_name or "orders-service", settings.otel_exporter_otlp_endpoint)
instrument_fastapi(app)
setup_metrics_endpoint(app)

log = get_logger(__name__)


# --- Модель запроса на создание заказа ---
class CreateOrderIn(BaseModel):
    order_id: str = Field(..., description="ID заказа")
    user_id: str = Field(..., description="ID пользователя")
    amount: float = Field(..., ge=0, description="Сумма заказа")


# --- Kafka продюсер ---
_producer = KafkaProducer()
_kafka_ready: bool = False


@app.on_event("startup")
async def _startup() -> None:
    # В unit‑тестах Kafka можно отключить через KAFKA_DISABLED=1
    if settings.kafka_disabled:
        log.info("kafka", msg="Kafka отключена переменной окружения")
        global _kafka_ready
        _kafka_ready = True
        return
    await _producer.start()
    global _kafka_ready
    _kafka_ready = True
    log.info("kafka", msg="Kafka продюсер запущен")


@app.on_event("shutdown")
async def _shutdown() -> None:
    if settings.kafka_disabled:
        return
    await _producer.stop()
    global _kafka_ready
    _kafka_ready = False
    log.info("kafka", msg="Kafka продюсер остановлен")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name or "orders-service"}


@app.get("/")
async def root() -> dict[str, str]:
    log.info("root", msg="Orders service alive")
    return {"message": "Orders service"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    if settings.kafka_disabled:
        return {"status": "ready", "kafka": "disabled"}
    if not _kafka_ready:
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}


@app.post("/orders")
async def create_order(data: CreateOrderIn) -> dict[str, str]:
    """Создать заказ и опубликовать событие OrderCreated в Kafka.

    В реальном проекте здесь была бы запись в БД и outbox.
    Для демо публикуем событие напрямую.
    """
    # Сформируем protobuf‑сообщение доменного события
    from common.proto.orders import orders_pb2  # ленивый импорт
    evt = orders_pb2.OrderCreated(order_id=data.order_id, user_id=data.user_id, amount=data.amount)
    payload = evt.SerializeToString()

    envelope = pack_envelope(
        payload=payload,
        event_type="OrderCreated",
        source=settings.service_name or "orders-service",
    )

    if settings.kafka_disabled:
        log.info("orders", msg="Kafka отключена, событие не отправлено", order_id=data.order_id)
    else:
        await _producer.send(ORDERS_EVENTS, envelope)
        log.info("orders", msg="OrderCreated опубликован", order_id=data.order_id)

    return {"status": "created", "order_id": data.order_id}
