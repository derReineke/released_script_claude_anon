"""Generate mock PDFs for testing the main_anon.py script."""

import random
from decimal import Decimal
from fpdf import FPDF


TRANSACTION_TYPES = [
    "NEW POLICIES",
    "REWRITES",
    "ADDED PREMIUM",
    "RETURN PREMIUM",
    "RENEWALS",
    "CANCELLATIONS",
]

# Insurance divisions for each page (matching main_anon.py)
PAGES = {
    4: "Insurance Division 4",
    5: "Insurance Division 5",
    7: "Insurance Division 7",
    8: "Insurance Division 8",
    10: "Insurance Division 10",
    11: "Insurance Division 11",
}

# Tennessee pages that should have all zeros
TENNESSEE_PAGES = [6, 9, 12]


def format_amount(amount: Decimal) -> str:
    """Format amount for PDF display."""
    if amount == 0:
        return ".00"
    if amount < 0:
        return f"{abs(amount):,.2f}CR"
    return f"{amount:,.2f}"


def generate_random_amount(min_val: int = 0, max_val: int = 50000) -> Decimal:
    """Generate a random dollar amount."""
    return Decimal(random.randint(min_val * 100, max_val * 100)) / 100


def generate_transaction_line(trans_type: str, is_zero: bool = False) -> str:
    """Generate a transaction line with amounts."""
    if is_zero:
        return f"{trans_type}  .00  .00  .00  .00  .00  .00"

    # Generate realistic amounts: GROSS, COMMISSION (15%), NET, then repeat
    gross = generate_random_amount(100, 25000)
    commission = (gross * Decimal("0.15")).quantize(Decimal("0.01"))
    net = gross - commission

    # Make RETURN PREMIUM and CANCELLATIONS potentially negative (CR)
    if trans_type in ["RETURN PREMIUM", "CANCELLATIONS"]:
        if random.random() > 0.3:  # 70% chance of being a credit
            gross = -abs(gross)
            commission = -abs(commission)
            net = -abs(net)

    return (
        f"{trans_type}  {format_amount(gross)}  {format_amount(commission)}  "
        f"{format_amount(net)}  .00  .00  .00"
    )


def create_page_content(page_num: int, pdf: FPDF) -> None:
    """Add content for a single page."""
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    # Header
    pdf.cell(0, 10, f"PREMIUM TRANSACTION REPORT - PAGE {page_num}", ln=True, align="C")
    pdf.ln(5)

    # Determine if this is a Tennessee (zero) page or data page
    is_tennessee = page_num in TENNESSEE_PAGES
    is_data_page = page_num in PAGES

    if is_data_page:
        company_name = PAGES[page_num]
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, company_name, ln=True)
        pdf.ln(3)
    elif is_tennessee:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "TENNESSEE DIVISION", ln=True)
        pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f"OTHER DIVISION - PAGE {page_num}", ln=True)
        pdf.ln(3)

    # Section header
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "DIRECT BILLED", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, "TRANS TYPE          GROSS      COMMISSION      NET      GROSS      COMMISSION      NET", ln=True)
    pdf.ln(3)

    # Transaction lines
    pdf.set_font("Courier", size=9)
    for trans_type in TRANSACTION_TYPES:
        line = generate_transaction_line(trans_type, is_zero=is_tennessee)
        pdf.cell(0, 5, line, ln=True)

    # Add some filler content
    pdf.ln(10)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 5, "AGENCY BILLED", ln=True)
    for trans_type in TRANSACTION_TYPES:
        line = generate_transaction_line(trans_type, is_zero=True)  # Agency billed is zeros
        pdf.cell(0, 5, line, ln=True)


def generate_mock_pdf(output_path: str, seed: int = None) -> None:
    """Generate a complete mock PDF with 12+ pages."""
    if seed is not None:
        random.seed(seed)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Generate 12 pages (matching the expected structure)
    for page_num in range(1, 13):
        create_page_content(page_num, pdf)

    pdf.output(output_path)
    print(f"Generated: {output_path}")


def main():
    import os

    # Create pdfs directory if it doesn't exist
    pdfs_dir = os.path.join(os.path.dirname(__file__), "pdfs")
    os.makedirs(pdfs_dir, exist_ok=True)

    # Generate PDFs for each day of the week
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    report_types = ["RELEASE_CBS", "ACCT_AND_STAT"]

    for report_type in report_types:
        for i, day in enumerate(days):
            output_path = os.path.join(pdfs_dir, f"{report_type}.{day}.PDF")
            # Use different seed for each file to get different data
            generate_mock_pdf(output_path, seed=hash(f"{report_type}_{day}"))

    print(f"\nGenerated {len(days) * len(report_types)} mock PDFs in {pdfs_dir}/")


if __name__ == "__main__":
    main()
