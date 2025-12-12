# Combined script to process both RELEASE_CBS and ACCT_AND_STAT PDFs
# Uses yesterday's date to determine which PDF files to process

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PdfLocation = Join-Path $ScriptDir "pdfs"
$OutputLocation = Join-Path $ScriptDir "output"

# Get yesterday's day abbreviation (Mon, Tue, Wed, etc.)
$ReportDate = (Get-Date).AddDays(-1)
$ReportDateShort = Get-Date -Date $ReportDate -UFormat %a

# Define the two report types
$Reports = @(
    @{
        Name = "RELEASE_CBS"
        PdfFile = "RELEASE_CBS.$ReportDateShort.PDF"
        CsvFile = "RELEASE_CBS.$ReportDateShort.csv"
    },
    @{
        Name = "ACCT_AND_STAT"
        PdfFile = "ACCT_AND_STAT.$ReportDateShort.PDF"
        CsvFile = "ACCT_AND_STAT.$ReportDateShort.csv"
    }
)

# Process each report
foreach ($Report in $Reports) {
    $PdfPath = Join-Path $PdfLocation $Report.PdfFile
    $CsvPath = Join-Path $OutputLocation $Report.CsvFile

    if (Test-Path $PdfPath) {
        Write-Host "Processing $($Report.Name)..." -ForegroundColor Cyan
        Set-Location $ScriptDir
        uv run python main.py $PdfPath -o $CsvPath

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Output: $CsvPath" -ForegroundColor Green
        } else {
            Write-Host "  Error processing $($Report.PdfFile)" -ForegroundColor Red
        }
    } else {
        Write-Host "PDF not found: $PdfPath" -ForegroundColor Yellow
    }
}

Write-Host "`nDone!" -ForegroundColor Cyan
