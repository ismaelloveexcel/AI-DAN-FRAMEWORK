#!/usr/bin/env bash
set -euo pipefail

echo "==> Validating AI-DAN framework stack"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Checking required env vars for auth-capable runs"
if [[ -z "${FRAMEWORK_API_KEY:-}" ]]; then
  echo "WARN: FRAMEWORK_API_KEY not set. Using validation fallback key."
  export FRAMEWORK_API_KEY="validation-key"
fi
if [[ -z "${ENABLE_AUTH:-}" ]]; then
  echo "WARN: ENABLE_AUTH not set. Defaulting to true for validation."
  export ENABLE_AUTH="true"
fi
export USE_MOCK_KB="${USE_MOCK_KB:-true}"

echo "==> Checking canonical n8n workflow files"
required_workflows=(
  "n8n_workflows/1_main_api_workflow.json"
  "n8n_workflows/2_chief_ai_agent_workflow.json"
  "n8n_workflows/3_sales_department_workflow.json"
  "n8n_workflows/4_outbound_sales_manager_workflow.json"
  "n8n_workflows/7_inbound_sales_manager_workflow.json"
  "n8n_workflows/8_marketing_department_workflow.json"
  "n8n_workflows/13_error_handling_workflow.json"
  "n8n_workflows/15_api_bridge_k8_connection.json"
)

for workflow in "${required_workflows[@]}"; do
  if [[ ! -f "$workflow" ]]; then
    echo "ERROR: Missing required workflow: $workflow"
    exit 1
  fi
done

echo "==> Running test suite"
pytest test_framework.py tests/test_n8n_integration.py tests/test_policy.py -v --tb=short

echo "==> Validation complete"
