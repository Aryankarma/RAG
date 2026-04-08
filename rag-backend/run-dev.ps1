# Backend dev server: moves Python/pip/uvm temp off C: if needed; activates venv; runs uvicorn.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$t = "E:\temp-pip-work"
if (Test-Path $t) {
    $env:TMPDIR = $t
    $env:TEMP = $t
    $env:TMP = $t
}

& "$root\venv\Scripts\Activate.ps1"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
