from __future__ import annotations

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def setup_metrics_endpoint(app) -> None:
    @app.get("/metrics")
    async def metrics() -> Response:  # type: ignore[override]
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
