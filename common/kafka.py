from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .config import get_settings


class KafkaProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self, *, retries: int = 10, initial_delay: float = 1.0) -> None:
        settings = get_settings()
        delay = initial_delay
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                self._producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_brokers)
                await self._producer.start()
                return
            except Exception as exc:  # брокер может быть ещё не готов
                last_exc = exc
                print(f"[kafka] producer start attempt {attempt}/{retries} failed: {exc}", flush=True)
                if attempt == retries:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)
        raise last_exc or RuntimeError("KafkaProducer start failed")

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def send(self, topic: str, value: bytes, key: bytes | None = None) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaProducer is not started")
        await self._producer.send_and_wait(topic, value=value, key=key)


class KafkaConsumerWorker:
    """Простой фоновый консьюмер Kafka для запуска внутри FastAPI.

    Пример использования:

    ```python
    consumer = KafkaConsumerWorker(
        topic="orders.events",
        group_id="orchestrator",
        handler=handle_message,
    )
    await consumer.start()
    # ... on shutdown: await consumer.stop()
    ```
    """

    def __init__(
        self,
        *,
        topic: str,
        group_id: str,
        handler: Callable[[bytes], Awaitable[None]],
        auto_offset_reset: str = "earliest",
    ) -> None:
        self._topic = topic
        self._group_id = group_id
        self._handler = handler
        self._auto_offset_reset = auto_offset_reset
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self, *, retries: int = 10, initial_delay: float = 1.0) -> None:
        settings = get_settings()
        delay = initial_delay
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                self._consumer = AIOKafkaConsumer(
                    self._topic,
                    bootstrap_servers=settings.kafka_brokers,
                    group_id=self._group_id,
                    enable_auto_commit=True,
                    auto_offset_reset=self._auto_offset_reset,
                )
                await self._consumer.start()
                self._task = asyncio.create_task(self._loop(), name=f"kafka-consumer-{self._topic}")
                return
            except Exception as exc:
                last_exc = exc
                print(f"[kafka] consumer start attempt {attempt}/{retries} failed: {exc}", flush=True)
                if attempt == retries:
                    break
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10.0)
        raise last_exc or RuntimeError("KafkaConsumer start failed")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _loop(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                try:
                    await self._handler(bytes(msg.value))
                except Exception:
                    # Здесь можно добавить ретраи/дедлеттер
                    # Пока просто логгируем через print, чтобы не тянуть логгер сюда
                    print(f"[kafka] handler error for topic {self._topic}", flush=True)
        except asyncio.CancelledError:
            pass


async def example_usage() -> None:
    """Мини-пример отправки сообщения. Используется только для отладки.
    Не вызывается в продакшене.
    """
    kp = KafkaProducer()
    await kp.start()
    try:
        await kp.send("example-topic", b"payload")
    finally:
        await kp.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())
