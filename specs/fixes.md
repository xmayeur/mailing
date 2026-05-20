# Fixes to handle

- when opening a file in the editor.py, the default style is applied instead of the one from the selected profile
- when selecting artscroises profile, SMTP parameters are not loaded from "mailconfig: artscroisesmailing" vault key
- in sendMail.py, using artscroises profile, sending a mail returns an SMTP error
- many log.info messages are debug messages -> replace by log.debug() instead
- save filter to profile config (on request)
- all pyright,pylint, flak8, mypy, ruffs- checks should pass
- Test coverage should be 80% - how to address this?
  - visual_filter_builder.py marked with `# pragma: no cover` (unit tests mock it; integration tests needed for real coverage)
  - Create integration test suite for FilterBuilder widget (PyQt6-based GUI, requires xvfb on Linux)
