googleDriveLib module
=====================

.. automodule:: googleDriveLib
   :members:
   :undoc-members:
   :show-inheritance:

Overview
--------

This module provides utilities for interacting with Google Drive API using a service account.
It is based on the guide: https://medium.com/@matheodaly.md/using-google-drive-api-with-python-and-a-service-account-d6ae1f6456c2

Functions
---------

Logging
^^^^^^^

.. autofunction:: googleDriveLib._init_log

Connection & Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: googleDriveLib.connect_google_driver

File Operations
^^^^^^^^^^^^^^^

.. autofunction:: googleDriveLib.get_files

.. autofunction:: googleDriveLib.download_file

.. autofunction:: googleDriveLib.upload_file

.. autofunction:: googleDriveLib.rename_file

Module Details
--------------

The module provides the following capabilities:

* **Authentication**: Connect to Google Drive using service account credentials
* **File Listing**: Retrieve files from specific folders with metadata
* **File Download**: Download files from Google Drive to local storage
* **File Upload**: Upload files to Google Drive
* **File Rename**: Rename files in Google Drive

Usage Example
-------------

.. code-block:: python

    import googleDriveLib as gd

    # Connect to Google Drive
    service = gd.connect_google_driver("myServiceAccount")

    # Get files from a folder
    files = gd.get_files(service, folder_id="your_folder_id")

    # Download files
    gd.download_file(service, files["files"], folder="downloads")

    # Rename a file
    gd.rename_file(service, fileId="file_id", newTitle="new_name.pdf")
