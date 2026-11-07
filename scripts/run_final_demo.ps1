param([ValidateSet('backend', 'frontend')][string]$Component = 'backend')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Component -eq 'backend') {
    $env:PYTHONPATH = "$projectRoot\src;$projectRoot"
    $env:PYTHONIOENCODING = 'utf-8'
    $env:RAG_INDEX_PATH = Join-Path $projectRoot 'data\index\engineering_faculty_20261107_v1'
    $env:MOCK_RULES_PATH = Join-Path $projectRoot '.local\integration_execution_20261107\mock_cases.json'
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'prepare_manual_mock_cases.py') --index $env:RAG_INDEX_PATH --output $env:MOCK_RULES_PATH
    if ($LASTEXITCODE -ne 0) { throw 'Offline mock evidence preparation failed' }
    $env:LLM_PROVIDER = 'mock'
    $env:ALLOW_FREE_API_CALLS = 'false'
    $env:ALLOW_PAID_API_CALLS = 'false'
    $env:GROQ_FREE_PLAN_CONFIRMED = 'false'
    $env:BACKEND_LOAD_DOTENV = 'false'
    $env:BACKEND_ENV_FILE = ''
    $env:BACKEND_CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
    $env:HF_HUB_OFFLINE = '1'
    $env:TRANSFORMERS_OFFLINE = '1'
    $env:HF_HUB_DISABLE_TELEMETRY = '1'
    $env:BACKEND_HOST = '127.0.0.1'
    $env:BACKEND_PORT = '8000'
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') -m backend
} else {
    Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    $env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
    npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
}
