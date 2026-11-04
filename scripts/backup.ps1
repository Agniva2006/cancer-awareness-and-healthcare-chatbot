# Requires: pg_dump on PATH (bundled with PostgreSQL / Docker).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/backup.ps1              # backup
#   powershell -ExecutionPolicy Bypass -File scripts/backup.ps1 -Restore backups\dump_20260211.sql  # restore drill
#
# Reads DATABASE_URL from .env (same as the app). Works with the local Docker
# Postgres (localhost:5433). For a managed DB (Render), point DATABASE_URL at
# the external connection string and run the same script.
param(
    [string]$RestoreFile = ""
)

$ErrorActionPreference = "Stop"

# Parse DATABASE_URL from .env
$envLine = (Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' }) -replace '^DATABASE_URL=', ''
if (-not $envLine) { Write-Error "DATABASE_URL not found in .env"; exit 1 }

$uri = [Uri]$envLine
$host_ = $uri.Host
$port = if ($uri.Port -gt 0) { $uri.Port } else { 5432 }
$db = $uri.AbsolutePath.TrimStart('/')
$user = $uri.UserInfo.Split(':')[0]
$pass = $uri.UserInfo.Split(':')[1]
$env:PGPASSWORD = $pass

if ($RestoreFile -ne "") {
    Write-Output ">> RESTORE drill: $RestoreFile -> $db on ${host_}:$port"
    Get-Content $RestoreFile | docker exec -i cancer_chatbot_db psql -U $user -d $db
    Write-Output ">> Restore done. Verify data with: docker exec cancer_chatbot_db psql -U $user -d $db -c 'SELECT count(*) FROM knowledge_documents;'"
} else {
    New-Item -ItemType Directory -Force -Path backups | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $out = "backups/${db}_${stamp}.sql"
    Write-Output ">> BACKUP: $db on ${host_}:$port -> $out"
    docker exec cancer_chatbot_db pg_dump -U $user -d $db | Set-Content -Path $out -Encoding UTF8
    Write-Output ">> Backup written ($((Get-Item $out).Length) bytes)."
    Write-Output ">> TEST YOUR RESTORE: powershell -File scripts/backup.ps1 -RestoreFile $out"
}
