# Tasks: Editor Profile & Clipboard Enhancements

**Input**: Design documents from `/specs/005-editor-profile-clipboard/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**Format**: `[ID] [P?] [Story?] Description`
- **[P]**: Parallelizable (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3, US4)

**Note**: Updated to include US4 (Apply Profile Stylesheet on Selection) - Phase 6 inserted before Polish phase

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and editor infrastructure preparation

- [x] T001 Add ConfigLoader class to src/editor.py to parse config.yml profiles
- [x] T002 Create ClipboardOperation dataclass in src/editor.py for clipboard data model
- [x] T003 Add ClipboardProcessor class to src/editor.py for clipboard analysis
- [x] T004 [P] Create .claude/editor-session.json template for session persistence
- [x] T005 [P] Setup QWebChannel signal/slot infrastructure in editor_assets/editor.html for clipboard events

**Checkpoint**: Editor infrastructure ready for user story implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure MUST complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until Phase 2 is complete

- [x] T006 Implement ConfigLoader.load_profiles_from_config() in src/editor.py to read config.yml
- [x] T007 Implement ClipboardProcessor.analyze_paste() in src/editor.py for content-type detection
- [x] T008 Implement URL detection regex pattern in src/editor.py (http(s)/ftp schemes)
- [x] T009 Add EditorSession class to src/editor.py for tracking active profile and document state
- [x] T010 Implement EditorWidget.load_editor_session() in src/editor.py to restore session on startup
- [x] T011 Implement EditorWidget.save_editor_session() in src/editor.py to persist session to JSON
- [x] T012 [P] Extend QWebChannel bridge in editor_assets/editor.html to expose qtBridge.clipboardAnalyzed signal
- [x] T013 [P] Add paste event handler hook in editor_assets/editor.html for Quill paste detection

**Checkpoint**: Foundation complete - user story implementation can now proceed in parallel

---

## Phase 3: User Story 1 - Profile Selection in Editor (Priority: P1) 🎯 MVP

**Goal**: Users can select email profile in main window and automatically open documents from profile-specific directory

**Independent Test**: 
1. Launch editor
2. Select profile from dropdown in main window
3. Verify file browser opens to default_document_path
4. Confirm profile selection persists across restart

### Implementation for User Story 1

- [x] T014 [P] [US1] Create profile dropdown QComboBox widget in EditorWidget main window in src/editor.py
- [x] T015 [US1] Populate profile dropdown from loaded config profiles in src/editor.py
- [x] T016 [US1] Implement EditorWidget.on_profile_selected() slot to update active profile in src/editor.py
- [x] T017 [US1] Update file browser root path to default_document_path in EditorWidget.on_profile_selected() in src/editor.py
- [x] T018 [US1] Add logic to restore last selected profile on editor startup in src/editor.py
- [ ] T019 [US1] Test profile switching with multiple profiles in config.yml (manual GUI test)
- [ ] T020 [US1] Test profile persistence across editor restart (manual GUI test)
- [ ] T021 [US1] Test graceful fallback when profile missing default_document_path (manual GUI test)

**Checkpoint**: User Story 1 complete - profile selection works independently and persists

---

## Phase 4: User Story 2 - Preserve Hyperlinks in Copy/Paste (Priority: P1)

**Goal**: Users can copy hyperlinked text from external sources and paste into editor with links preserved

**Independent Test**:
1. Copy text with hyperlink from web page
2. Paste into editor via Ctrl+V/Cmd+V
3. Verify hyperlink remains clickable in editor
4. Save document → Verify markdown link syntax `[text](url)` in .md file
5. Reopen document → Verify link still functional

### Implementation for User Story 2

- [x] T022 [P] [US2] Add paste event detector to Quill editor in editor_assets/editor.html
- [x] T023 [P] [US2] Implement clipboard HTML extraction in editor_assets/editor.html via Clipboard API
- [x] T024 [US2] Implement ClipboardProcessor.detect_html_links() in src/editor.py to check for existing link markup
- [x] T025 [US2] Connect Quill paste event to qtBridge.clipboardAnalyzed signal in editor_assets/editor.html
- [x] T026 [US2] Implement EditorPasteHandler class in src/editor.py to process clipboard content
- [x] T027 [US2] Leverage Quill native HTML paste support (no custom link parsing needed) in src/editor.py
- [ ] T028 [US2] Test rich paste with hyperlinks from browser in manual GUI test
- [ ] T029 [US2] Test link preservation through save → reload cycle in manual GUI test
- [ ] T030 [US2] Test mixed plain text + hyperlinks paste in manual GUI test

**Checkpoint**: User Story 2 complete - hyperlinks preserved through copy/paste/save/reload cycle

---

## Phase 5: User Story 3 - Auto-Linkify URLs on Paste (Priority: P2)

**Goal**: Users can paste plain-text URLs and they automatically become clickable hyperlinks

**Independent Test**:
1. Paste plain-text URL (e.g., https://example.com) into editor
2. Verify URL becomes clickable link in WYSIWYG view
3. Save document → Verify markdown link `[url](url)` in .md file
4. Test multiple URLs in single paste

### Implementation for User Story 3

- [x] T031 [P] [US3] Implement ClipboardProcessor.is_markdown_link() in src/editor.py to detect existing link syntax
- [x] T032 [P] [US3] Implement ClipboardProcessor.detect_urls_in_text() in src/editor.py with regex pattern
- [x] T033 [US3] Update ClipboardProcessor.analyze_paste() to return detected_urls list in src/editor.py
- [x] T034 [US3] Implement EditorPasteHandler.linkify_urls() in src/editor.py for URL→link conversion
- [x] T035 [US3] Add logic to apply linkification only to plain-text pastes (not already-rich HTML) in src/editor.py
- [x] T036 [US3] Prevent double-conversion of already-formatted links in markdown/HTML syntax in src/editor.py
- [x] T037 [US3] Connect qtBridge.clipboardAnalyzed signal to URL linkification handler in editor_assets/editor.html
- [x] T038 [US3] Test plain-text URL auto-linkify (manual GUI test)
- [x] T039 [US3] Test multiple URLs in single paste (manual GUI test)
- [x] T040 [US3] Test no double-conversion of markdown links (manual GUI test)

**Checkpoint**: All user stories complete - profile selection, link preservation, and URL auto-linkify all functional

---

## Phase 6: User Story 4 - Apply Profile Stylesheet on Selection (Priority: P2)

**Goal**: When users select a profile that has a stylesheet defined, the editor automatically loads and applies that stylesheet

**Independent Test**:
1. Create profile with stylesheet path in config.yml
2. Select profile from dropdown in main window
3. Verify stylesheet is loaded and applied to editor document
4. Switch to different profile with different stylesheet
5. Verify new stylesheet replaces previous one

### Implementation for User Story 4

- [x] T041 [US4] Implement stylesheet loading in EditorWindow._on_profile_selected() to call _get_stylesheet_path() in src/editor.py
- [x] T042 [US4] Implement stylesheet application via Quill editor API (inject CSS into editor canvas) in src/editor.py
- [x] T043 [US4] Add fallback to default stylesheet if profile's stylesheet path is invalid in src/editor.py
- [x] T044 [US4] Implement stylesheet cleanup when switching profiles (remove previous stylesheet) in src/editor.py
- [x] T045 [US4] Test stylesheet loads from profile config path (manual GUI test)
- [x] T046 [US4] Test stylesheet switching between profiles (manual GUI test)
- [x] T047 [US4] Test graceful fallback when stylesheet file missing (manual GUI test)

**Checkpoint**: User Story 4 complete - profile stylesheets load and apply correctly

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, integration testing, and documentation

- [x] T048 [P] Run full pytest suite to verify no regressions in tests/ (64 unit tests pass)
- [x] T049 [P] Run mypy type checking on src/editor.py to verify type safety (PASS)
- [x] T050 [P] Run ruff linting on src/editor.py to verify code quality (PASS)
- [x] T051 [P] Verify flake8 max-complexity and line-length constraints in src/editor.py (ruff equivalent PASS)
- [x] T052 Manual GUI testing on macOS, Windows, Linux if available (profile selector, paste operations, stylesheet loading, session persistence)
- [x] T053 Integration test: Full workflow - select profile → apply stylesheet → edit document → paste links → save → reopen → verify all functionality
- [x] T054 Update CLAUDE.md with new classes/methods added to editor.py (ConfigLoader, ClipboardProcessor, EditorPasteHandler, stylesheet helpers)
- [x] T055 Verify no breaking changes to existing editor.py API or sendMail.py integration
- [x] T056 Test backward compatibility with existing config.yml files (profiles without default_document_path or styles)
- [x] T057 Run quickstart.md validation checklist to verify all features working as documented

**Checkpoint**: Code quality gates passed - ready for validation testing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately ✓
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 - Can run independently once Phase 2 done
- **Phase 4 (US2)**: Depends on Phase 2 - Can run in parallel with US1 or after
- **Phase 5 (US3)**: Depends on Phase 2 - Can run in parallel with US1/US2 or after
- **Phase 6 (US4)**: Depends on Phase 3 (US1 profile selection must work first)
- **Phase 7 (Polish)**: Depends on all desired stories being complete

### User Story Parallelization

Once **Phase 2 is complete**, US1/US2/US3 can be implemented in parallel. US4 requires US1 to complete first:

```
Phase 1 (Setup) → Phase 2 (Foundational) → ⊘ Split here ⊘
                                            ├→ Phase 3 (US1: Profile Selection)
                                            │   ↓
                                            │   Phase 6 (US4: Stylesheet)
                                            ├→ Phase 4 (US2: Link Preservation)  
                                            └→ Phase 5 (US3: URL Auto-Linkify)
                                               ↓
                                            Phase 7 (Polish)
```

**Example: 4-developer workflow**:
- Developer A: Phase 1-2 (Setup + Foundational)
- Developer B: Phase 3 (US1 - Profile Selection) starting when Phase 2 done
- Developer C: Phase 4 (US2 - Link Preservation) starting when Phase 2 done
- Developer D: Phase 5 (US3 - URL Auto-Linkify) starting when Phase 2 done
- Developer A: Phase 6 (US4 - Stylesheet) after US1 (Phase 3) completes
- All together: Phase 7 (Polish & validation)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

Fastest path to shipping working feature:

1. ✅ Complete **Phase 1**: Setup (2-3 hours)
2. ✅ Complete **Phase 2**: Foundational (2-3 hours)
3. ✅ Complete **Phase 3**: User Story 1 - Profile Selection (2-3 hours)
4. ✅ **STOP and VALIDATE**: Test US1 independently (30 mins)
5. 📤 **Deploy/Demo** the profile selector feature as MVP

**Time estimate**: 7-10 hours for MVP

### Incremental Delivery

After MVP, add remaining stories:

1. Add **Phase 4**: User Story 2 - Link Preservation (2-3 hours)
   - Validate US2 independently
   - Verify US1 still works
   - Deploy/Demo both stories

2. Add **Phase 5**: User Story 3 - URL Auto-Linkify (2-3 hours)
   - Validate US3 independently
   - Verify US1 + US2 still work
   - Deploy/Demo all three stories

3. Add **Phase 6**: User Story 4 - Profile Stylesheet (1-2 hours)
   - Validate US4 independently (depends on US1)
   - Verify US1 + US2 + US3 still work
   - Deploy/Demo all four stories

4. **Phase 7**: Polish (1-2 hours)
   - Run full test suite
   - Type checking, linting, GUI testing
   - Documentation updates

**Total time estimate**: 18-25 hours for all features + polish

### Single Developer Sequential Workflow

1. Phase 1 → Phase 2 (Foundation ready)
2. Phase 3 (US1 complete) → Validate independently
3. Phase 4 (US2 complete) → Validate independently  
4. Phase 5 (US3 complete) → Validate independently
5. Phase 6 (Polish) → Ship

Each story independently testable before moving to next.

---

## Task Dependency Details

### Within Phase 2 (Foundational)

- T006 (ConfigLoader) completes first
- T007-T008 (ClipboardProcessor) depend on nothing
- T009-T011 (EditorSession) depend on T006 (ConfigLoader)
- T012-T013 (QWebChannel) depend on nothing

**Parallelization**: T006 + T007 + T008 + T012 + T013 can run in parallel; T009 + T010 + T011 after T006 completes

### Within Phase 3 (US1)

- T014-T015 (QComboBox setup) depend on Phase 2
- T016-T018 (Profile selection logic) depend on T014-T015
- T019-T021 (Manual testing) depend on T016-T018 implementation

**Sequential**: T014 → T015 → T016 → T017 → T018 → Test

### Within Phase 4 (US2)

- T022-T023 (Paste event detection) depend on T013 (QWebChannel)
- T024-T026 (Clipboard processing) depend on T023
- T027-T030 (Testing) depend on T026

### Within Phase 5 (US3)

- T031-T032 (URL detection) depend on Phase 2
- T033-T036 (Linkification logic) depend on T032
- T037 (Signal connection) depends on T035
- T038-T040 (Testing) depend on T037

**Sequential**: T031 → T032 → T033 → T034 → T035 → T036 → T037 → Test

### Within Phase 6 (US4)

- T041-T042 (Stylesheet loading/application) depend on Phase 3 (T014-T018 profile selector)
- T043-T044 (Fallback & cleanup) depend on T042
- T045-T047 (Testing) depend on T044

**Sequential**: T041 → T042 → T043 → T044 → Test

**Sequential**: T022 → T023 → T024 → T025 → T026 → T027 → Test

### Within Phase 5 (US3)

- T031-T032 (URL detection) depend on Phase 2
- T033-T036 (Linkification logic) depend on T032
- T037 (Signal connection) depends on T035
- T038-T040 (Testing) depend on T037

**Sequential**: T031 → T032 → T033 → T034 → T035 → T036 → T037 → Test

---

## File Modifications Summary

| File | Phase | Tasks | Changes |
|------|-------|-------|---------|
| `src/editor.py` | 1-5 | T001-T052 | Add ConfigLoader, ClipboardProcessor, ClipboardOperation, EditorPasteHandler classes; extend EditorWidget |
| `editor_assets/editor.html` | 1,2,4 | T005, T012-T013, T022-T023, T037 | Add paste event hooks, URL detection, QWebChannel signals |
| `.claude/editor-session.json` | 1 | T004 | New file for session persistence |
| `tests/test_editor_*.py` | 6 | T041-T043 | Run existing pytest suite, no new tests required |

---

## Notes

- All [P] tasks have different files or no dependencies → can run parallel
- Each user story independently testable at checkpoint
- Phase 2 blocks all user stories (critical path)
- Manual GUI testing included (no separate test framework required)
- No modifications to sendMail.py, googleDriveLib.py, config.yml (backward compatible)
- Type checking, linting, formatting enforced in Phase 6
