param(
    [switch]$Reset,
    [switch]$InitOnly
)

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SetupScript = Join-Path $BackendDir "setup_and_run.py"

$Arguments = @()
if ($Reset) {
    $Arguments += "--reset"
}
if ($InitOnly) {
    $Arguments += "--init-only"
}

python $SetupScript @Arguments

if ($LASTEXITCODE -ne 0) {
    exit 1
}

