"""
Утилиты для упаковки/распаковки событий в конверт `EventEnvelope`.

Мы не привязываемся к конкретным protobuf-классам здесь — сервисы сами
сериализуют свои сообщения в bytes и передают сюда. Это упрощает импорт
в средах, где прото-код ещё не сгенерирован (например, при запуске unit-тестов).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

# ВАЖНО: импортируем pb2 только внутри функций, чтобы не падать, если прото ещё не сгенерен


def _now_iso() -> str:
    """Возвращает UTC-время в ISO8601."""
    return datetime.now(UTC).isoformat()


def pack_envelope(
    *,
    payload: bytes,
    event_type: str,
    source: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    traceparent: str | None = None,
) -> bytes:
    """
    Упаковать произвольный payload (bytes) в `EventEnvelope`.

    - event_type — строковое имя события (например, "OrderCreated").
    - source — имя сервиса-источника.
    """
    from common.proto.common import event_envelope_pb2 as env_pb2  # локальный импорт
    env_pb2 = cast(Any, env_pb2)  # для mypy: tr-typed pb2 считаем Any

    env = env_pb2.EventEnvelope(
        id=str(uuid4()),
        type=event_type,
        source=source,
        correlation_id=correlation_id or "",
        causation_id=causation_id or "",
        traceparent=traceparent or "",
        timestamp=_now_iso(),
        payload=payload,
    )
    return cast(bytes, env.SerializeToString())


def unpack_envelope(data: bytes) -> tuple[Any, bytes]:
    """
    Распаковать bytes в `EventEnvelope` и вернуть кортеж (envelope, payload_bytes).
    Возвращаем сам envelope (protobuf-объект) и исходный payload (bytes).
    """
    from common.proto.common import event_envelope_pb2 as env_pb2  # локальный импорт
    env_pb2 = cast(Any, env_pb2)  # для mypy

    env = env_pb2.EventEnvelope()
    env.ParseFromString(data)
    return env, bytes(env.payload)
