# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF data extraction tool that parses insurance premium transaction reports. Extracts GROSS values from the DIRECT BILLED section for 6 divisions (Insurance Division 4, Insurance Division 5, Insurance Division 7, Insurance Division 8, Insurance Division 10, Insurance Division 11).

## Commands

```bash
# Install dependencies
uv sync

# Run extraction (prints to console)
uv run python main_anon.py <filename.pdf>

# Run extraction with CSV output
uv run python main_anon.py <filename.pdf> -o output.csv

# Run tests
uv run pytest test_main.py

# Run tests with verbose output
uv run pytest test_main.py -v

# Run tests with coverage report
uv run pytest test_main.py --cov=main_anon
```

## Architecture

Single-file script (`main_anon.py`) using pdfplumber's text extraction with regex parsing.

**Key components:**
- `PAGES` dict: Maps PDF page numbers to division names (pages 4,5,7,8,10,11)
- `extract_page_data()`: Extracts text, uses regex to find transaction types and their GROSS values
- `parse_amount()`: Handles "CR" suffix (credits become negative), commas, and zero formatting

**PDF structure:**
- Pages 1-3: Summary pages (ignored)
- Pages 4-5: Insurance Division 4/5
- Pages 6: Division 6 (ignored - always zeros)
- Pages 7-8: Insurance Division 7/8
- Pages 9: Division 9 (ignored)
- Pages 10-11: Insurance Division 10/11
- Page 12: Division 12 (ignored)

**Transaction types extracted:** NEW POLICIES, REWRITES, ADDED PREMIUM, RETURN PREMIUM, RENEWALS, CANCELLATIONS

PDF files go in `pdfs/`, CSV outputs go in `output/`.

## Testing

The project includes comprehensive unit tests in `test_main.py` covering:

- **Amount parsing**: Handles commas, CR suffix (credits), zero values, and whitespace
- **Amount formatting**: Ensures proper .00 formatting for zeros and 2 decimal places
- **Page data extraction**: Tests single/multiple transactions, credits, zero values, and all transaction types
- **CSV writing**: Verifies directory creation, content formatting, and multi-company output
- **PDF extraction**: Tests page processing, missing pages, and company name mapping
- **Constants validation**: Ensures PAGES and TRANSACTION_TYPES are correctly configured

All tests use mocking to avoid requiring actual PDF files.
