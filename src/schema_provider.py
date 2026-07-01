"""Database schema extraction for filter validation.

Extracts field names (headers) from CSV and Google Sheets databases.
Used by filter editor to provide field name suggestions and validate
that filter fields exist in the subscriber database.

Classes:
    DatabaseSchemaProvider: Detects database type and extracts schema
"""

import csv
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("schema_provider")


class DatabaseSchemaProvider:
    """Extract field names (schema) from database sources."""

    @staticmethod
    def from_csv(csv_path: str) -> list[str]:
        """Extract field names from CSV file headers.

        Args:
            csv_path: Path to CSV file

        Returns:
            List of field names from first row (headers)
        """
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                return [h.strip() for h in headers if h.strip()]
        except (OSError, StopIteration) as e:
            log.debug("Could not read CSV headers: %s", e)
            return []

    @staticmethod
    def from_excel(excel_path: str, sheet_name: str | None = None) -> list[str]:
        """Extract field names from Excel file (XLSX/XLS) headers.

        Uses python-calamine (same as sendMail.py) for reading Excel files.

        Args:
            excel_path: Path to Excel file
            sheet_name: Sheet name (if None, uses first sheet)

        Returns:
            List of field names from first row (headers)
        """
        try:
            from python_calamine import CalamineWorkbook

            wb = CalamineWorkbook.from_path(excel_path)
            # Get sheet by name if specified, otherwise first sheet
            ws = None
            if sheet_name:
                for i, name in enumerate(wb.sheet_names):
                    if name == sheet_name:
                        ws = wb.get_sheet_by_index(i)
                        break
                if ws is None:
                    log.debug("Could not find sheet in Excel file: %s", sheet_name)
                    return []
            else:
                ws = wb.get_sheet_by_index(0)

            # First row contains headers
            data = ws.to_python()
            if data and len(data) > 0:
                headers = data[0]
                return [str(h).strip() for h in headers if h and str(h).strip()]
            return []
        except ImportError:
            log.error("python-calamine not available for Excel support")
            return []
        except Exception as e:
            log.debug("Could not read Excel headers: %s", e)
            return []

    @staticmethod
    def _get_worksheet(service: Any, sheet_name: str | None = None) -> Any:
        """Get worksheet by name or first if None."""
        worksheets = service.worksheets()
        if not worksheets:
            return None
        if not sheet_name:
            return worksheets[0]
        for worksheet in worksheets:
            if worksheet.title == sheet_name:
                return worksheet
        return None

    @staticmethod
    def from_google_sheets(
        service: Any, spreadsheet_id: str, sheet_name: str | None = None  # noqa: ARG004
    ) -> list[str]:
        """Extract field names from Google Sheets first row.

        Args:
            service: Google Sheets service object (from gspread or google-api-python-client)
            spreadsheet_id: Spreadsheet ID (unused in gspread, service already bound)
            sheet_name: Sheet name (if None, uses first sheet)

        Returns:
            List of field names from first row
        """
        try:
            if not hasattr(service, "worksheets"):
                log.debug("Service object is not a gspread Spreadsheet")
                return []
            ws = DatabaseSchemaProvider._get_worksheet(service, sheet_name)
            if ws is None:
                log.debug("Sheet %s not found", sheet_name)
                return []
            headers = ws.row_values(1)
            return [h.strip() for h in headers if h.strip()]
        except Exception as e:
            log.debug("Could not read Google Sheets headers: %s", e)
            return []

    @staticmethod
    def detect_and_extract(database_path: str, sheet_name: str | None = None, gsheet_service: Any = None) -> list[str]:
        """Detect database type and extract schema.

        B009: Support CSV, Excel (XLSX/XLS), and Google Sheets databases.

        Args:
            database_path: Path to CSV/Excel file or Google Sheets URL/ID
            sheet_name: Sheet name for Excel/Google Sheets
            gsheet_service: Google Sheets service object

        Returns:
            List of field names
        """
        if not database_path:
            return []

        path = Path(database_path)
        suffix = path.suffix.lower()

        if suffix == ".csv":
            if path.exists():
                return DatabaseSchemaProvider.from_csv(database_path)
            log.warning("CSV database file not found: %s", database_path)
            return []

        # B009: Handle Excel files (XLSX, XLS)
        if suffix in (".xlsx", ".xls"):
            if path.exists():
                return DatabaseSchemaProvider.from_excel(database_path, sheet_name)
            log.warning("Excel database file not found: %s", database_path)
            return []

        if gsheet_service and ("docs.google" in database_path or len(database_path) > 20):
            return DatabaseSchemaProvider.from_google_sheets(gsheet_service, database_path, sheet_name)

        # B016: Distinguish between file not found and unknown type
        if suffix in (".csv", ".xlsx", ".xls"):
            log.warning("Database file not found: %s", database_path)
        else:
            log.debug("Unknown database type: %s", database_path)
        return []
