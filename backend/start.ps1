param(
    [switch]$Reset,
    [switch]$InitOnly
)

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupScript = Join-Path $BackendDir "setup_and_run.py"
$ProjectRoot = Split-Path -Parent $BackendDir
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { "python" }

$Arguments = @()
if ($Reset) {
    $Arguments += "--reset"
}
if ($InitOnly) {
    $Arguments += "--init-only"
}

& $Python $SetupScript @Arguments

if ($LASTEXITCODE -ne 0) {
    exit 1
}

