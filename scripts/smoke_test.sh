#!/usr/bin/env bash

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"

echo "========================================"
echo "Enterprise Analyst AI Stack Smoke Test"
echo "========================================"
echo "API base URL: ${API_BASE_URL}"
echo

echo "[1/3] Checking health endpoint..."
curl --fail --silent --show-error \
  "${API_BASE_URL}/health"
echo
echo

echo "[2/3] Creating deterministic analysis..."
RESPONSE_FILE="$(mktemp)"

curl --fail --silent --show-error \
  --request POST \
  --header "Content-Type: application/json" \
  --data '{
    "tenant_id": "tenant-demo",
    "workspace_id": "workspace-customer-intelligence",
    "user_id": "analyst-001",
    "capability_id": "customer-churn-analysis",
    "query": "Explain why customer churn increased during Q2 and provide an evidence-backed executive summary."
  }' \
  "${API_BASE_URL}/api/v1/analyses" \
  > "${RESPONSE_FILE}"

cat "${RESPONSE_FILE}"
echo
echo

echo "[3/3] Validating response contract..."
python3 - "${RESPONSE_FILE}" <<'PY'
import json
import sys
from pathlib import Path

response_path = Path(sys.argv[1])
payload = json.loads(response_path.read_text(encoding="utf-8"))

required_fields = {
    "analysis_id",
    "trace_id",
    "status",
    "summary",
    "findings",
    "evidence",
    "policy_decision",
    "evaluation",
    "runtime",
}

missing = required_fields.difference(payload)

if missing:
    raise SystemExit(f"Missing response fields: {sorted(missing)}")

if payload["status"] != "COMPLETED":
    raise SystemExit(f"Unexpected analysis status: {payload['status']}")

if payload["policy_decision"]["decision"] != "ALLOW":
    raise SystemExit("Expected policy decision ALLOW.")

if payload["evaluation"]["decision"] != "PASS":
    raise SystemExit("Expected evaluation decision PASS.")

print("[PASS] Deterministic analysis response is valid.")
print(f"Analysis ID: {payload['analysis_id']}")
print(f"Trace ID: {payload['trace_id']}")
PY

rm -f "${RESPONSE_FILE}"

echo
echo "Smoke test completed successfully."
