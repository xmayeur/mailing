Filter Validator Module
=======================

Overview
--------

The **filter_validator** module provides YAML filter syntax validation and
field name checking for the newsletter editor UI.

When users edit filters in the editor, this module:

* Validates YAML syntax
* Checks that filter field names exist in the subscriber database
* Reports validation errors for user feedback

.. automodule:: filter_validator
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

FilterValidator
^^^^^^^^^^^^^^^

.. autoclass:: filter_validator.FilterValidator
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Validate a filter against a subscriber database schema::

    from filter_validator import FilterValidator
    from schema_provider import DatabaseSchemaProvider

    validator = FilterValidator()
    schema = DatabaseSchemaProvider.from_csv('subscribers.csv')

    # Check filter syntax
    status = validator.get_validation_status(
        filter_text="email: is not empty\nstatus: is active",
        database_schema=schema
    )

    if status['is_valid']:
        print("Filter is valid")
    else:
        print("Errors:", status['syntax_errors'])
        print("Missing fields:", status['missing_fields'])
