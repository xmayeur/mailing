"""Database schema extraction utilities for filter validation.

Extracts field names from CSV and Google Sheets databases.
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
        except (OSError, FileNotFoundError, StopIteration) as e:
            log.warning("Could not read CSV headers: %s", e)
            return []

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
            # Assume service is gspread Spreadsheet object
            if hasattr(service, "worksheets"):
                ws = None
                if not sheet_name:
                    ws = service.worksheets()[0] if service.worksheets() else None
                else:
                    for worksheet in service.worksheets():
                        if worksheet.title == sheet_name:
                            ws = worksheet
                            break
                if ws is None:
                    log.warning("Sheet %s not found", sheet_name)
                    return []
                headers = ws.row_values(1)
                return [h.strip() for h in headers if h.strip()]
            else:
                log.warning("Service object is not a gspread Spreadsheet")
                return []
        except Exception as e:
            log.warning("Could not read Google Sheets headers: %s", e)
            return []

    @staticmethod
    def detect_and_extract(
        database_path: str, sheet_name: str | None = None, gsheet_service: Any = None
    ) -> list[str]:
        """Detect database type and extract schema.

        Args:
            database_path: Path to CSV file or Google Sheets URL/ID
            sheet_name: Sheet name for Google Sheets
            gsheet_service: Google Sheets service object

        Returns:
            List of field names
        """
        if not database_path:
            return []

        path = Path(database_path)

        if path.suffix.lower() == ".csv" and path.exists():
            return DatabaseSchemaProvider.from_csv(database_path)

        if gsheet_service and ("docs.google" in database_path or len(database_path) > 20):
            return DatabaseSchemaProvider.from_google_sheets(
                gsheet_service, database_path, sheet_name
            )

        log.warning("Unknown database type: %s", database_path)
        return []
