FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev bash protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/common.txt

COPY . .

RUN bash scripts/gen_protos.sh

EXPOSE 8002
CMD ["uvicorn", "services.payments.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
