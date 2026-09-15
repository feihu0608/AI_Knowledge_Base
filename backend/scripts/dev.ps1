$ErrorActionPreference = 'Stop'
$BackendRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = @(
  'apps/api', 'packages/domain', 'packages/application', 'packages/agent_harness',
  'packages/graphs', 'packages/providers', 'packages/retrieval', 'packages/vector_store',
  'packages/persistence', 'packages/mcp_gateway', 'packages/observability', 'packages/evaluation'
) -join ';'
Set-Location $BackendRoot
python -m uvicorn knowledge_api.main:app --host 0.0.0.0 --port 8080 --reload
