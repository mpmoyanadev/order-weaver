#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="common/proto"
mkdir -p "$OUT_DIR"
touch "$OUT_DIR/__init__.py"
mkdir -p "$OUT_DIR/common" "$OUT_DIR/orders" "$OUT_DIR/payments" "$OUT_DIR/inventory"
touch "$OUT_DIR/common/__init__.py" "$OUT_DIR/orders/__init__.py" "$OUT_DIR/payments/__init__.py" "$OUT_DIR/inventory/__init__.py"

if command -v protoc >/dev/null 2>&1; then
  protoc \
    -I proto \
    --python_out="$OUT_DIR" \
    proto/common/event_envelope.proto \
    proto/orders/orders.proto \
    proto/payments/payments.proto \
    proto/inventory/inventory.proto
else
  python -m grpc_tools.protoc \
    -I proto \
    --python_out="$OUT_DIR" \
    proto/common/event_envelope.proto \
    proto/orders/orders.proto \
    proto/payments/payments.proto \
    proto/inventory/inventory.proto
fi

echo "Прото‑классы сгенерированы в $OUT_DIR"
