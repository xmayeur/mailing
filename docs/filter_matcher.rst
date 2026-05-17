Filter Matcher Module
=====================

Overview
--------

The **filter_matcher** module provides filter matching for the newsletter editor UI.

It wraps sendMail's filtering logic to:

* Apply filters to subscriber rows in the editor
* Show live preview of filtered results
* Validate filters against actual data

.. automodule:: filter_matcher
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

FilterMatcher
^^^^^^^^^^^^^

.. autoclass:: filter_matcher.FilterMatcher
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Single row filtering
^^^^^^^^^^^^^^^^^^^^

Check if a single row matches filter criteria::

    from filter_matcher import FilterMatcher

    matcher = FilterMatcher()

    # Headers and row data
    headers = ['id', 'name', 'email', 'status']
    row = [1, 'John', 'john@example.com', 'active']

    # Filter (field -> "operator value")
    filter_dict = {'status': 'is active', 'email': 'is not empty'}

    # Returns True if row matches (should be INCLUDED)
    if matcher.match_row(row, filter_dict, headers):
        print("Row matches filter")
    else:
        print("Row filtered out")

Multiple rows filtering
^^^^^^^^^^^^^^^^^^^^^^^

Filter a dataset to show preview::

    rows = [
        [1, 'John', 'john@example.com', 'active'],
        [2, 'Jane', 'jane@example.com', 'inactive'],
        [3, 'Bob', 'bob@example.com', 'active'],
    ]

    filtered = matcher.filter_rows(rows, filter_dict, headers)
    print(f"Matched {len(filtered)} of {len(rows)} rows")

Get filter results with count
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get both filtered results and original count for statistics::

    filtered, total = matcher.filter_rows_with_count(
        rows, filter_dict, headers
    )
    print(f"Selected {len(filtered)} of {total} subscribers")
