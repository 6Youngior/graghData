param(
    [string]$Python = 'D:\anaconda3\envs\agent\python.exe',
    [switch]$RerunExperiments,
    [switch]$SkipBrowserCheck
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
function Invoke-ProjectPython {
    param([string[]]$InvocationArgs)
    & $Python @InvocationArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed: python $InvocationArgs" }
}
Push-Location -LiteralPath $projectRoot
try {
    Invoke-ProjectPython -InvocationArgs @('code/test_kreach.py')
    Invoke-ProjectPython -InvocationArgs @('code/test_dominance.py')
    if ($RerunExperiments) {
        Invoke-ProjectPython -InvocationArgs @('code/scripts/acquire.py')
        Invoke-ProjectPython -InvocationArgs @('code/kreach_experiments.py','--force')
        foreach ($coverSeed in @(29,43)) {
            Invoke-ProjectPython -InvocationArgs @('code/kreach_experiments.py','--cover-seed',"$coverSeed",'--ks','4','--seeds','17','--force')
        }
        Invoke-ProjectPython -InvocationArgs @('code/dominance_experiments.py','--force')
        foreach ($coverSeed in @(29,43)) {
            Invoke-ProjectPython -InvocationArgs @('code/dominance_experiments.py','--cover-seed',"$coverSeed",'--ks','4','--seeds','17','--force')
        }
        Invoke-ProjectPython -InvocationArgs @('code/dominance_synthetic.py')
    }
    Invoke-ProjectPython -InvocationArgs @('code/verify_kreach.py')
    Invoke-ProjectPython -InvocationArgs @('code/verify_dominance.py')
    Invoke-ProjectPython -InvocationArgs @('code/kreach_figures.py')
    Invoke-ProjectPython -InvocationArgs @('code/write_kreach_report.py')
    Invoke-ProjectPython -InvocationArgs @('code/dominance_figures.py')
    Invoke-ProjectPython -InvocationArgs @('code/write_dominance_report.py')
    Invoke-ProjectPython -InvocationArgs @('code/build_kreach_demo.py')
    if (-not $SkipBrowserCheck) { Invoke-ProjectPython -InvocationArgs @('code/scripts/render_comparison_video.py') }
    & node visualization/test_paper_engine.js
    if ($LASTEXITCODE -ne 0) { throw 'Demo cross-language check failed' }
    & node visualization/test_dominance_engine.js
    if ($LASTEXITCODE -ne 0) { throw 'Dominance demo cross-language check failed' }
    Invoke-ProjectPython -InvocationArgs @('code/scripts/build_slides.py')
    Invoke-ProjectPython -InvocationArgs @('code/scripts/preview_pdf.py')
    Invoke-ProjectPython -InvocationArgs @('code/scripts/check_theme.py')
    if (-not $SkipBrowserCheck) { Invoke-ProjectPython -InvocationArgs @('code/scripts/check_paper_demo.py') }
    Invoke-ProjectPython -InvocationArgs @('code/scripts/final_check.py')
} finally {
    Pop-Location
}

