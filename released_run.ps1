Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project-local main.py so we don't depend on network paths
$ScriptPath = Join-Path -Path $PSScriptRoot -ChildPath 'main_anon.py'

# Use yesterday's day-of-week short name (e.g., Mon, Tue, Wed, Thu, Fri)
$ReportDateShort = (Get-Date).AddDays(-1).ToString('ddd')

# Filenames expected by the Python script (PDFs live under the 'pdfs' folder)
$AcctPdf = "ACCT_AND_STAT.$ReportDateShort.PDF"
$AcctOut = "ACCT_AND_STAT.$ReportDateShort.csv"

$CbsPdf = "RELEASE_CBS.$ReportDateShort.PDF"
$CbsOut = "RELEASE_CBS.$ReportDateShort.csv"

Write-Host "Running extraction for $AcctPdf -> output/$AcctOut" -ForegroundColor Cyan
& uv run python $ScriptPath $AcctPdf -o $AcctOut

Write-Host "Running extraction for $CbsPdf -> output/$CbsOut" -ForegroundColor Cyan
& uv run python $ScriptPath $CbsPdf -o $CbsOut

Write-Host "Done." -ForegroundColor Green