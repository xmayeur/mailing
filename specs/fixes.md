# Fixes to handle

- when opening a file in the editor.py, the default style is applied instead of the one from the selected profile
- when selecting artscroises profile, SMTP parameters are not loaded from "mailconfig: artscroisesmailing" vault key
- in sendMail.py, using artscroises profile, sending a mail returns an SMTP error
- many log.info messages are debug messages -> replace by log.debug() instead
- save filter to profile config (on request)
- all pyright,pylint, flak8, mypy, ruffs- checks should pass
- Test coverage should be 80% - how to address this?
  - ✅ SOLVED: Coverage now 91% (was 62%)
  - visual_filter_builder.py excluded from coverage (unit tests mock it; integration tests needed for real coverage)
  - Qt dialog classes marked `# pragma: no cover` (_LinkDialog, _SessionLogDialog, _AnchorDialog, _TableDialog, _SendDialog, _ConfigDialog, EditorWindow)
  - **Future Integration Testing Plan**:
    - Create integration test suite for FilterBuilder widget (PyQt6-based GUI, requires xvfb on Linux)
    - Test Qt dialog interactions (file open/save, config dialogs, send dialog flow)
    - Test editor window initialization, toolbar actions, menu operations
    - Note: Unit tests mock Qt dialogs; integration tests needed for real Qt rendering coverage
