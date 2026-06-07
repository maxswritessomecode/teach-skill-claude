# Generic Action Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture app-general keyboard shortcuts, drag selections, and post-action screenshots so recordings preserve formatting and selection intent across Excel, Word, PowerPoint, browsers, and other apps.

**Architecture:** Extend `InputCounter` to classify shortcut and typed input signals. Extend `RecorderController` to emit `keyboard_shortcut`, `drag_select`, and `post_action_capture` events while reusing the existing screenshot writer and privacy filter. Keep raw typed content behind the existing `capture_raw_keystrokes` config.

**Tech Stack:** Python, pynput key/mouse callbacks, pytest.

---

## Tasks

- [ ] Add tests for shortcut detection and typed-text privacy gating in `tests/test_input.py`.
- [ ] Add controller tests for shortcut events, post-click screenshots, drag selections, and paused capture suppression in `tests/test_recorder_controller.py`.
- [ ] Implement generic shortcut state in `src/teach_skill/recorder/input.py`.
- [ ] Implement controller shortcut, drag, and post-action screenshot event emission in `src/teach_skill/recorder/controller.py`.
- [ ] Update tray mouse listener to pass movement/release callbacks in `src/teach_skill/recorder/tray.py`.
- [ ] Run focused and full verification.
