import argparse
import csv
import os
import re
from decimal import Decimal
from typing import NamedTuple

import pdfplumber

# Page numbers (1-indexed) mapped to anonymized division names
# Pages 6, 9, 12 are Tennessee pages - skipped as they're always zeros
PAGES = {
    4: "Insurance Division 4",
    5: "Insurance Division 5",
    7: "Insurance Division 7",
    8: "Insurance Division 8",
    10: "Insurance Division 10",
    11: "Insurance Division 11",
}

TRANSACTION_TYPES = [
    "NEW POLICIES",
    "REWRITES",
    "ADDED PREMIUM",
    "RETURN PREMIUM",
    "RENEWALS",
    "CANCELLATIONS",
]

CSV_HEADERS = [
    "Company",
    "New Policies",
    "Rewrites",
    "Added Premium",
    "Return Premium",
    "Renewals",
    "Cancellations",
]

# Pattern to match a transaction line:
# TRANS_TYPE  GROSS  COMMISSION  NET  GROSS  COMMISSION  NET
# e.g., "NEW POLICIES 21,149.00 3,172.35 17,976.65 .00 .00 .00"
AMOUNT_PATTERN = r"[\d,]+\.\d{2}(?:CR)?"
LINE_PATTERN = re.compile(
    rf"^({'|'.join(TRANSACTION_TYPES)})\s+({AMOUNT_PATTERN})",
    re.MULTILINE
)


class CompanyData(NamedTuple):
    company: str
    new_policies: Decimal
    rewrites: Decimal
    added_premium: Decimal
    return_premium: Decimal
    renewals: Decimal
    cancellations: Decimal


def parse_amount(value: str) -> Decimal:
    """Parse a dollar amount string into a Decimal.

    Handles:
    - ".00" -> 0
    - "CR" suffix -> negative
    - Commas in numbers
    """
    value = value.strip()
    if value == ".00":
        return Decimal("0")

    is_credit = value.endswith("CR")
    if is_credit:
        value = value[:-2]

    value = value.replace(",", "")

    try:
        amount = Decimal(value)
    except Exception:
        return Decimal("0")

    return -amount if is_credit else amount


def extract_page_data(page: pdfplumber.page.Page, company: str) -> CompanyData | None:
    """Extract transaction data from a single page using text extraction."""
    text = page.extract_text()
    if not text:
        return None

    # Find all transaction type lines and extract the first GROSS value
    values = {}
    for match in LINE_PATTERN.finditer(text):
        trans_type = match.group(1)
        gross = match.group(2)
        # Only take the first occurrence (DIRECT BILLED section)
        if trans_type not in values:
            values[trans_type] = parse_amount(gross)

    if not values:
        return None

    return CompanyData(
        company=company,
        new_policies=values.get("NEW POLICIES", Decimal("0")),
        rewrites=values.get("REWRITES", Decimal("0")),
        added_premium=values.get("ADDED PREMIUM", Decimal("0")),
        return_premium=values.get("RETURN PREMIUM", Decimal("0")),
        renewals=values.get("RENEWALS", Decimal("0")),
        cancellations=values.get("CANCELLATIONS", Decimal("0")),
    )


def extract_pdf(pdf_path: str) -> list[CompanyData]:
    """Extract all company data from a PDF file."""
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, company in PAGES.items():
            if page_num > len(pdf.pages):
                print(f"Warning: Page {page_num} not in PDF")
                continue

            page = pdf.pages[page_num - 1]  # 0-indexed
            data = extract_page_data(page, company)

            if data:
                results.append(data)
            else:
                print(f"Warning: Could not extract data from page {page_num}")

    return results


def format_amount(amount: Decimal) -> str:
    """Format a Decimal as a string with 2 decimal places.

    Uses '.00' format for zero values to match expected output.
    """
    if amount == 0:
        return ".00"
    return f"{amount:.2f}"


def write_csv(data: list[CompanyData], output_path: str) -> None:
    """Write extracted data to a CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for row in data:
            writer.writerow([
                row.company,
                format_amount(row.new_policies),
                format_amount(row.rewrites),
                format_amount(row.added_premium),
                format_amount(row.return_premium),
                format_amount(row.renewals),
                format_amount(row.cancellations),
            ])


def print_data(data: list[CompanyData]) -> None:
    """Print extracted data to console."""
    for row in data:
        print(f"\n--- {row.company} ---")
        print(f"New Policies: {format_amount(row.new_policies)}")
        print(f"Rewrites: {format_amount(row.rewrites)}")
        print(f"Added Premium: {format_amount(row.added_premium)}")
        print(f"Return Premium: {format_amount(row.return_premium)}")
        print(f"Renewals: {format_amount(row.renewals)}")
        print(f"Cancellations: {format_amount(row.cancellations)}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract financial data from premium transaction PDFs."
    )
    parser.add_argument(
        "filename",
        help="Name of the PDF file in the 'pdfs/' directory."
    )
    parser.add_argument(
        "-o", "--output",
        help="Name of the output CSV file in the 'output/' directory."
    )

    args = parser.parse_args()

    pdf_path = os.path.join("pdfs", args.filename)

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return 1

    data = extract_pdf(pdf_path)

    if not data:
        print("No data was extracted.")
        return 1

    if args.output:
        output_path = os.path.join("output", args.output)
        write_csv(data, output_path)
        print(f"Saved to {output_path}")
    else:
        print_data(data)

    return 0


if __name__ == "__main__":
    exit(main())
