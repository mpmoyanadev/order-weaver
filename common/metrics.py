from __future__ import annotations

from typing import Any

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def setup_metrics_endpoint(app: Any) -> None:
    @app.get("/metrics")
    async def metrics() -> Response:  # type: ignore[override]
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
