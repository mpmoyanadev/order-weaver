from __future__ import annotations

from fastapi import FastAPI, HTTPException

from common.config import get_settings
from common.events import pack_envelope, unpack_envelope
from common.kafka import KafkaConsumerWorker, KafkaProducer
from common.logging import get_logger, setup_logging
from common.metrics import setup_metrics_endpoint
from common.otel import instrument_fastapi, setup_otel
from common.topics import PAYMENTS_COMMANDS, PAYMENTS_EVENTS

settings = get_settings()

app = FastAPI(title="OrderWeaver - Payments", version="0.1.0")

setup_logging(settings.service_name or "payments-service")
setup_otel(settings.service_name or "payments-service", settings.otel_exporter_otlp_endpoint)
instrument_fastapi(app)
setup_metrics_endpoint(app)

log = get_logger(__name__)

# --- Kafka ---
_producer = KafkaProducer()
_commands_consumer: KafkaConsumerWorker | None = None
_kafka_ready: bool = False


async def _handle_payment_command(data: bytes) -> None:
    """Обработка команд платежей.

    Сейчас поддерживаем PaymentAuthorize и публикуем PaymentCaptured (демо‑логика).
    """
    env, payload = unpack_envelope(data)
    if env.type != "PaymentAuthorize":
        return

    # Ленивая загрузка protobuf‑классов
    from common.proto.payments import payments_pb2

    # Имитируем успешный захват платежа
    captured = payments_pb2.PaymentCaptured(order_id="")
    # Извлекаем order_id из команды
    cmd = payments_pb2.PaymentAuthorize()
    cmd.ParseFromString(payload)
    captured.order_id = cmd.order_id

    out_env = pack_envelope(
        payload=captured.SerializeToString(),
        event_type="PaymentCaptured",
        source=settings.service_name or "payments-service",
        correlation_id=env.correlation_id or env.id,
        causation_id=env.id,
        traceparent=env.traceparent,
    )
    await _producer.send(PAYMENTS_EVENTS, out_env)
    log.info("payments", msg="Опубликовано событие PaymentCaptured", order_id=captured.order_id)


@app.on_event("startup")
async def _startup() -> None:
    if settings.kafka_disabled:
        log.info("kafka", msg="Kafka отключена переменной окружения")
        global _kafka_ready
        _kafka_ready = True
        return
    await _producer.start()
    global _commands_consumer
    _commands_consumer = KafkaConsumerWorker(
        topic=PAYMENTS_COMMANDS,
        group_id="payments",
        handler=_handle_payment_command,
        auto_offset_reset="earliest",
    )
    await _commands_consumer.start()
    global _kafka_ready
    _kafka_ready = True
    log.info("kafka", msg="Payments подключен к Kafka")


@app.on_event("shutdown")
async def _shutdown() -> None:
    if settings.kafka_disabled:
        return
    if _commands_consumer is not None:
        await _commands_consumer.stop()
    await _producer.stop()
    global _kafka_ready
    _kafka_ready = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name or "payments-service"}


@app.get("/")
async def root() -> dict[str, str]:
    log.info("root", msg="Payments service alive")
    return {"message": "Payments service"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    if settings.kafka_disabled:
        return {"status": "ready", "kafka": "disabled"}
    if not _kafka_ready:
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}
