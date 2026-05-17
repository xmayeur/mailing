# Research: Loading Indicator Enhancement for Filter Application

**Feature**: Filter Editor with Database Preview (001-filter-editor-database)  
**Enhancement**: Add running clock/progress indicator during filter application & data fetch  
**Date**: 2026-05-17

## Requirement

Display visual feedback while filter is being applied and records are being fetched from database. User should see animated clock or spinner indicating operation in progress.

**Why needed**: 
- Large databases (1000+ records) may take 100-300ms to filter
- User needs confirmation that operation is ongoing, not frozen
- Prevents multiple clicks while filtering

## Design Options

### Option A: Animated Clock (QLabel with rotating text)
- **Implementation**: Timer + text rotation ("🕐 🕑 🕒...")
- **Pros**: Simple, matches user request ("running clock"), minimal dependencies
- **Cons**: Text-based rotation less smooth than CSS spinner

### Option B: QProgressBar (Indeterminate)
- **Implementation**: QProgressBar with `setRange(0, 0)` for animated state
- **Pros**: Standard Qt widget, familiar pattern, smooth animation
- **Cons**: Takes screen space, different from "clock" request

### Option C: Qt Spinner/Loading Animation
- **Implementation**: Custom QMovie or QSvgWidget with spinner animation
- **Pros**: Professional appearance, smooth animation
- **Cons**: Requires asset file or SVG embed, more setup

### Option D: Status Label with Animated Text
- **Implementation**: QLabel with timer updating text ("|/-\\" rotation or emoji clock)
- **Pros**: Lightweight, uses existing status label, simple
- **Cons**: Text-based animation may look choppy

## Chosen Solution: Option A (Animated Clock Emoji)

**Rationale**: 
- Directly matches user request ("running clock")
- Minimal code changes (use existing filter_status_label)
- Works with existing QTimer infrastructure
- No external assets needed

**Implementation**:
```python
# During filter_and_display_records():
clock_frames = ['🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛']
# Rotate through frames every 100ms while filtering
# Update filter_status_label with current frame
```

## Technical Approach

1. **Show clock**: Before `filter_and_display_records()` starts, start timer updating label
2. **Animate**: Every 100ms, rotate to next clock emoji
3. **Hide clock**: When `filter_and_display_records()` completes, stop timer, show result status

**Code Location**: src/editor.py `_SendDialog._apply_filter()` and `filter_and_display_records()`

**State Management**:
- Add instance variable: `_filtering_in_progress` (bool)
- Add instance variable: `_clock_frame_index` (int) for animation state
- Reuse existing `_validation_timer` or create `_loading_timer`

## Integration Points

- `_apply_filter()`: Start clock before filter operation
- `filter_and_display_records()`: Animate clock, then hide on completion
- Existing error handling: Stop clock if error occurs
- Cancel behavior: Stop clock if user cancels dialog

## Performance Impact

- Minimal: Timer fires every 100ms (10 FPS), lightweight label update
- No blocking of main thread (Qt event loop handles timer)
- Clock animation independent from filtering operation

## Testing Strategy

- Unit test: Clock animation frames rotate correctly
- Integration test: Clock appears during filter operation, disappears when complete
- Edge cases: Clock stops on error, cancel, empty filter
