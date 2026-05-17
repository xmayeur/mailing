Schema Provider Module
======================

Overview
--------

The **schema_provider** module extracts database schema (field names) from
CSV and Google Sheets sources.

Used by the filter editor to:

* Detect database type (CSV vs Google Sheets)
* Extract field names from headers
* Provide field suggestions and validation

.. automodule:: schema_provider
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

DatabaseSchemaProvider
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: schema_provider.DatabaseSchemaProvider
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Extract schema from CSV file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract field names from a local CSV database::

    from schema_provider import DatabaseSchemaProvider

    schema = DatabaseSchemaProvider.from_csv('subscribers.csv')
    print(schema)
    # Output: ['id', 'first_name', 'last_name', 'email', 'status', ...]

Extract schema from Google Sheets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract field names from Google Sheets (requires gspread service object)::

    from schema_provider import DatabaseSchemaProvider
    import gspread

    # Assuming you have a gspread service object
    service = gspread.authorize(creds)
    spreadsheet = service.open_by_key('sheet_id')

    schema = DatabaseSchemaProvider.from_google_sheets(
        spreadsheet,
        spreadsheet_id='sheet_id',
        sheet_name='Members'
    )

Auto-detect database type
^^^^^^^^^^^^^^^^^^^^^^^^^

Automatically detect CSV vs Google Sheets and extract schema::

    from schema_provider import DatabaseSchemaProvider

    # CSV file
    schema = DatabaseSchemaProvider.detect_and_extract('subscribers.csv')

    # Google Sheets (requires gsheet_service)
    schema = DatabaseSchemaProvider.detect_and_extract(
        'https://docs.google.com/spreadsheets/d/...',
        gsheet_service=spreadsheet_obj
    )
