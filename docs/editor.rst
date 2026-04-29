editor module
=============

Overview
--------

The **editor** module provides the standalone WYSIWYG newsletter editor used by
sendMail. It contains the Qt bridge, the editor window, the configuration
dialogs, and the helper functions that support HTML editing, file selection,
and editor startup.

Module API
----------

.. automodule:: editor
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Classes
-------

.. autoclass:: editor._LinkDialog
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor._AnchorDialog
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor._TableDialog
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor._SendDialog
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor._LineFieldSpec
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor._ConfigDialog
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor.EditorBridge
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: editor.EditorWindow
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: editor._svg_icon

.. autofunction:: editor.main
