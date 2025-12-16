import csv
import os
from decimal import Decimal
from unittest.mock import Mock, patch, mock_open

import pytest

from main_anon import (
    PAGES,
    TRANSACTION_TYPES,
    CompanyData,
    parse_amount,
    extract_page_data,
    format_amount,
    write_csv,
    extract_pdf,
)


class TestParseAmount:
    """Tests for parse_amount function."""

    def test_zero_value(self):
        """Test parsing .00 returns Decimal zero."""
        assert parse_amount(".00") == Decimal("0")

    def test_simple_amount(self):
        """Test parsing simple dollar amount."""
        assert parse_amount("100.50") == Decimal("100.50")

    def test_amount_with_commas(self):
        """Test parsing amount with comma separators."""
        assert parse_amount("21,149.00") == Decimal("21149.00")

    def test_large_amount_with_multiple_commas(self):
        """Test parsing large amounts with multiple commas."""
        assert parse_amount("1,234,567.89") == Decimal("1234567.89")

    def test_credit_suffix(self):
        """Test parsing amount with CR suffix returns negative."""
        assert parse_amount("100.00CR") == Decimal("-100.00")

    def test_credit_with_commas(self):
        """Test parsing amount with both commas and CR suffix."""
        assert parse_amount("1,500.50CR") == Decimal("-1500.50")

    def test_whitespace_handling(self):
        """Test parsing handles whitespace."""
        assert parse_amount("  100.50  ") == Decimal("100.50")

    def test_invalid_value_returns_zero(self):
        """Test invalid amounts return zero."""
        assert parse_amount("invalid") == Decimal("0")
        assert parse_amount("") == Decimal("0")

    def test_decimal_precision(self):
        """Test parsing maintains decimal precision."""
        assert parse_amount("123.45") == Decimal("123.45")


class TestFormatAmount:
    """Tests for format_amount function."""

    def test_zero_formatting(self):
        """Test zero is formatted as .00."""
        assert format_amount(Decimal("0")) == ".00"

    def test_positive_amount(self):
        """Test positive amount formatting."""
        assert format_amount(Decimal("100.50")) == "100.50"

    def test_negative_amount(self):
        """Test negative amount formatting."""
        assert format_amount(Decimal("-100.50")) == "-100.50"

    def test_large_amount(self):
        """Test large amount formatting."""
        assert format_amount(Decimal("21149.00")) == "21149.00"

    def test_precision_rounding(self):
        """Test amounts are formatted with 2 decimal places."""
        assert format_amount(Decimal("100.456")) == "100.46"
        assert format_amount(Decimal("100.1")) == "100.10"


class TestExtractPageData:
    """Tests for extract_page_data function."""

    def test_extract_single_transaction(self):
        """Test extracting a single transaction type."""
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "DIRECT BILLED SECTION\n"
            "NEW POLICIES 21,149.00 3,172.35 17,976.65\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        assert result.company == "Test Company"
        assert result.new_policies == Decimal("21149.00")
        assert result.rewrites == Decimal("0")

    def test_extract_multiple_transactions(self):
        """Test extracting multiple transaction types."""
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "DIRECT BILLED SECTION\n"
            "NEW POLICIES 21,149.00 3,172.35 17,976.65\n"
            "REWRITES 5,000.00 750.00 4,250.00\n"
            "RENEWALS 10,500.50 1,575.08 8,925.42\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        assert result.new_policies == Decimal("21149.00")
        assert result.rewrites == Decimal("5000.00")
        assert result.renewals == Decimal("10500.50")

    def test_extract_with_zero_values(self):
        """Test extracting with .00 zero values."""
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "NEW POLICIES .00 .00 .00\n"
            "REWRITES .00 .00 .00\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        assert result.new_policies == Decimal("0")
        assert result.rewrites == Decimal("0")

    def test_extract_with_credits(self):
        """Test extracting amounts with CR suffix."""
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "RETURN PREMIUM 1,500.00CR 225.00CR 1,275.00CR\n"
            "CANCELLATIONS 2,000.00CR 300.00CR 1,700.00CR\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        assert result.return_premium == Decimal("-1500.00")
        assert result.cancellations == Decimal("-2000.00")

    def test_extract_all_transaction_types(self):
        """Test extracting all six transaction types."""
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "NEW POLICIES 1,000.00 150.00 850.00\n"
            "REWRITES 2,000.00 300.00 1,700.00\n"
            "ADDED PREMIUM 3,000.00 450.00 2,550.00\n"
            "RETURN PREMIUM 500.00CR 75.00CR 425.00CR\n"
            "RENEWALS 4,000.00 600.00 3,400.00\n"
            "CANCELLATIONS 1,500.00CR 225.00CR 1,275.00CR\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        assert result.new_policies == Decimal("1000.00")
        assert result.rewrites == Decimal("2000.00")
        assert result.added_premium == Decimal("3000.00")
        assert result.return_premium == Decimal("-500.00")
        assert result.renewals == Decimal("4000.00")
        assert result.cancellations == Decimal("-1500.00")

    def test_extract_only_first_occurrence(self):
        """Test that only the first occurrence of each transaction type is extracted."""
        mock_page = Mock()
        # Simulating DIRECT BILLED section with first value, then AGENCY BILLED with second
        mock_page.extract_text.return_value = (
            "DIRECT BILLED\n"
            "NEW POLICIES 1,000.00 150.00 850.00\n"
            "AGENCY BILLED\n"
            "NEW POLICIES 2,000.00 300.00 1,700.00\n"
        )

        result = extract_page_data(mock_page, "Test Company")

        assert result is not None
        # Should only capture the first occurrence (1,000.00)
        assert result.new_policies == Decimal("1000.00")

    def test_empty_text_returns_none(self):
        """Test that empty page text returns None."""
        mock_page = Mock()
        mock_page.extract_text.return_value = None

        result = extract_page_data(mock_page, "Test Company")

        assert result is None

    def test_no_matching_transactions_returns_none(self):
        """Test that page with no matching transactions returns None."""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Some random text without transactions"

        result = extract_page_data(mock_page, "Test Company")

        assert result is None


class TestWriteCSV:
    """Tests for write_csv function."""

    def test_write_csv_creates_directory(self, tmp_path):
        """Test that write_csv creates output directory if it doesn't exist."""
        output_path = tmp_path / "output" / "test.csv"
        data = [
            CompanyData(
                company="Test Company",
                new_policies=Decimal("1000.00"),
                rewrites=Decimal("0"),
                added_premium=Decimal("500.00"),
                return_premium=Decimal("-100.00"),
                renewals=Decimal("2000.00"),
                cancellations=Decimal("0"),
            )
        ]

        write_csv(data, str(output_path))

        assert output_path.exists()

    def test_write_csv_content(self, tmp_path):
        """Test CSV content is correctly formatted."""
        output_path = tmp_path / "test.csv"
        data = [
            CompanyData(
                company="Insurance Division 4",
                new_policies=Decimal("21149.00"),
                rewrites=Decimal("0"),
                added_premium=Decimal("1500.50"),
                return_premium=Decimal("-500.00"),
                renewals=Decimal("10000.00"),
                cancellations=Decimal("0"),
            )
        ]

        write_csv(data, str(output_path))

        with open(output_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2  # Header + 1 data row
        assert rows[0] == [
            "Company",
            "New Policies",
            "Rewrites",
            "Added Premium",
            "Return Premium",
            "Renewals",
            "Cancellations",
        ]
        assert rows[1] == [
            "Insurance Division 4",
            "21149.00",
            ".00",
            "1500.50",
            "-500.00",
            "10000.00",
            ".00",
        ]

    def test_write_csv_multiple_companies(self, tmp_path):
        """Test CSV with multiple company rows."""
        output_path = tmp_path / "test.csv"
        data = [
            CompanyData(
                company="Company A",
                new_policies=Decimal("1000.00"),
                rewrites=Decimal("0"),
                added_premium=Decimal("0"),
                return_premium=Decimal("0"),
                renewals=Decimal("0"),
                cancellations=Decimal("0"),
            ),
            CompanyData(
                company="Company B",
                new_policies=Decimal("2000.00"),
                rewrites=Decimal("500.00"),
                added_premium=Decimal("0"),
                return_premium=Decimal("0"),
                renewals=Decimal("0"),
                cancellations=Decimal("0"),
            ),
        ]

        write_csv(data, str(output_path))

        with open(output_path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 3  # Header + 2 data rows


class TestExtractPDF:
    """Tests for extract_pdf function."""

    @patch("main_anon.pdfplumber.open")
    def test_extract_pdf_all_pages(self, mock_pdfplumber_open):
        """Test extracting data from all configured pages."""
        # Create mock PDF with 12 pages
        mock_pdf = Mock()
        mock_pages = []
        for i in range(12):
            mock_page = Mock()
            if i + 1 in PAGES:  # Pages 4,5,7,8,10,11 (0-indexed: 3,4,6,7,9,10)
                mock_page.extract_text.return_value = (
                    "NEW POLICIES 1,000.00 150.00 850.00\n"
                )
            else:
                mock_page.extract_text.return_value = "Other content"
            mock_pages.append(mock_page)

        mock_pdf.pages = mock_pages
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        results = extract_pdf("test.pdf")

        assert len(results) == 6  # 6 configured pages
        assert all(isinstance(data, CompanyData) for data in results)

    @patch("main_anon.pdfplumber.open")
    def test_extract_pdf_missing_page(self, mock_pdfplumber_open, capsys):
        """Test handling when PDF has fewer pages than expected."""
        mock_pdf = Mock()
        mock_pdf.pages = [Mock()]  # Only 1 page instead of 12

        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        results = extract_pdf("test.pdf")

        captured = capsys.readouterr()
        assert "Warning: Page" in captured.out
        assert len(results) == 0  # No pages successfully extracted

    @patch("main_anon.pdfplumber.open")
    def test_extract_pdf_correct_company_names(self, mock_pdfplumber_open):
        """Test that correct company names are assigned to pages."""
        mock_pdf = Mock()
        mock_pages = []
        for i in range(12):
            mock_page = Mock()
            mock_page.extract_text.return_value = (
                "NEW POLICIES 1,000.00 150.00 850.00\n"
            )
            mock_pages.append(mock_page)

        mock_pdf.pages = mock_pages
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        results = extract_pdf("test.pdf")

        expected_companies = [
            "Insurance Division 4",
            "Insurance Division 5",
            "Insurance Division 7",
            "Insurance Division 8",
            "Insurance Division 10",
            "Insurance Division 11",
        ]

        company_names = [data.company for data in results]
        assert company_names == expected_companies


class TestConstants:
    """Tests for module constants."""

    def test_pages_configuration(self):
        """Test PAGES constant has correct configuration."""
        assert len(PAGES) == 6
        assert 4 in PAGES
        assert 5 in PAGES
        assert 7 in PAGES
        assert 8 in PAGES
        assert 10 in PAGES
        assert 11 in PAGES
        # Tennessee pages (6, 9, 12) should not be included
        assert 6 not in PAGES
        assert 9 not in PAGES
        assert 12 not in PAGES

    def test_transaction_types_count(self):
        """Test all expected transaction types are defined."""
        assert len(TRANSACTION_TYPES) == 6
        assert "NEW POLICIES" in TRANSACTION_TYPES
        assert "REWRITES" in TRANSACTION_TYPES
        assert "ADDED PREMIUM" in TRANSACTION_TYPES
        assert "RETURN PREMIUM" in TRANSACTION_TYPES
        assert "RENEWALS" in TRANSACTION_TYPES
        assert "CANCELLATIONS" in TRANSACTION_TYPES


class TestCompanyData:
    """Tests for CompanyData NamedTuple."""

    def test_company_data_creation(self):
        """Test creating a CompanyData instance."""
        data = CompanyData(
            company="Test Company",
            new_policies=Decimal("1000.00"),
            rewrites=Decimal("0"),
            added_premium=Decimal("500.00"),
            return_premium=Decimal("-100.00"),
            renewals=Decimal("2000.00"),
            cancellations=Decimal("0"),
        )

        assert data.company == "Test Company"
        assert data.new_policies == Decimal("1000.00")
        assert data.return_premium == Decimal("-100.00")

    def test_company_data_immutable(self):
        """Test that CompanyData is immutable."""
        data = CompanyData(
            company="Test Company",
            new_policies=Decimal("1000.00"),
            rewrites=Decimal("0"),
            added_premium=Decimal("0"),
            return_premium=Decimal("0"),
            renewals=Decimal("0"),
            cancellations=Decimal("0"),
        )

        with pytest.raises(AttributeError):
            data.company = "New Company"
