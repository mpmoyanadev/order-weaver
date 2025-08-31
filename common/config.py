from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env",), extra="ignore")

    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4318", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    service_name: str = Field(default="service", alias="OTEL_SERVICE_NAME")
    kafka_brokers: str = Field(default="localhost:9092", alias="KAFKA_BROKERS")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    otel_disabled: bool = Field(default=False, alias="OTEL_DISABLED")
    # Позволяет полностью отключить Kafka (например, для unit‑тестов)
    kafka_disabled: bool = Field(default=False, alias="KAFKA_DISABLED")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
