# Implementation Plan: Loading Indicator Enhancement

**Branch**: `001-filter-editor-database` | **Date**: 2026-05-17 | **Spec
**: [Filter Editor Feature](/specs/001-filter-editor-database/spec.md)
**Input**: Enhancement request: "display a running clock while filter is applied and data are fetched"

**Note**: Enhancement to existing Filter Editor feature (prior bug fix complete).

## Summary

Add animated loading indicator (running clock emoji) to provide visual feedback during filter application and record
fetch. User sees rotating clock (🕐 🕑 🕒...) while records are being filtered/displayed, confirming operation in progress.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: PyQt6 (existing QTimer, QLabel)  
**Storage**: CSV or Google Sheets (no storage changes)  
**Testing**: pytest with Qt mocking  
**Target Platform**: macOS/Linux/Windows desktop  
**Project Type**: Desktop application GUI enhancement  
**Performance Goals**: Clock animation smooth (10 FPS = 100ms interval), non-blocking  
**Constraints**: Filter operation must complete <300ms (existing constraint)  
**Scale/Scope**: Single dialog enhancement, minimal scope

## Constitution Check

Constitution file is template-only. No violations detected.

## Project Structure

```text
src/editor.py
└── _SendDialog._apply_filter()                    # Start clock
    _SendDialog.filter_and_display_records()       # Animate during fetch, stop on complete
```

## Design: Animated Clock Emoji

**Implementation**:

- Clock frames: `['🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛']`
- Interval: 100ms per frame (10 FPS)
- Location: Existing `filter_status_label` widget
- Trigger: When `_apply_filter()` calls `filter_and_display_records()`
- Stop: When display updates complete

**State Flow**:

```
[Apply Filter Clicked]
  ↓
[Start clock: "🕐 Filtering..."]
  ↓
[Rotate emoji every 100ms while filtering]
  ↓
[Complete: "✓ Session filter applied"]
```

## Code Changes Required

1. Add instance variables:
    - `_clock_frame_index: int = 0`
    - `_loading_timer: QTimer | None = None`

2. Add method `_start_loading_clock()`:
    - Create/start QTimer with 100ms interval
    - Update label with rotating clock emoji

3. Add method `_stop_loading_clock()`:
    - Stop timer
    - Clear frame index

4. Modify `_apply_filter()`:
    - Call `_start_loading_clock()` before filter operation
    - Call `_stop_loading_clock()` after complete

5. Modify `filter_and_display_records()`:
    - Integrate clock animation into method flow
    - Ensure clock stops on error paths

## Testing

- Unit test: Clock frames rotate correctly
- Integration test: Clock visible during filter, hidden on completion
- Edge cases: Error paths, cancel, empty filter
- Regression: All 23 existing filter tests pass
