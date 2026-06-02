# PySide6 Record And Review Shell Design

**Date:** 2026-06-02
**Status:** Approved design direction
**Repo:** https://github.com/maxswritessomecode/teach-skill-claude
**Platform:** Windows first, portable UI architecture

## Overview

Teach Skill Claude should replace the bare Tkinter launcher with a modern
PySide6/Qt desktop shell focused on the Record And Review workflow.

The product flow should feel like:

```text
Record task -> review capture -> redact/exclude sensitive parts -> send to Agent SDK -> review/save skill
```

The app remains Windows-first because the current recorder depends on Windows
desktop capture behavior. The Qt shell should be structured so the UI can run
on other platforms later, but the product should not claim macOS/Linux recording
support until separate recorder backends exist.

## Goals

- Give nontechnical users a clear, modern app surface.
- Make recording state obvious.
- Let users inspect what was captured before Agent SDK compilation.
- Let users exclude events or screenshots before compile.
- Keep existing Python recorder, compiler, logging, diagnostics, and packaging
  code reusable.
- Validate PySide6 packaging before fully replacing the launcher.

## Non-Goals

- Full visual workflow editor.
- Voice narration.
- Skill chains.
- Native macOS/Linux recording.
- Replacing the Agent SDK compiler.
- A Tauri/React or native WinUI rewrite.

## Chosen Approach

Use PySide6/Qt as the modern desktop shell.

The Qt app will call into existing Python modules where possible and will launch
the current recorder and compiler through narrow service boundaries. This avoids
adding a second frontend/runtime stack before the workflow is validated.

Alternatives considered:

- **Tauri + React:** best long-term UI runway, but adds Rust, Node, web build
  tooling, IPC complexity, and packaging risk around a Python core.
- **Native Windows shell:** best Windows polish, but weak macOS path and would
  force C#/WinUI/WPF plus Python interop.

## Architecture

```text
Qt shell
  -> setup/status service
  -> recordings service
  -> review model
  -> recorder process service
  -> compiler process/service
  -> logs/support bundle service

Existing backend
  -> doctor checks
  -> recorder modules
  -> JSONL recording files
  -> screenshots
  -> Agent SDK compiler
  -> runtime logs
```

The UI should avoid embedding recorder internals directly. It should consume
small data models and invoke small service methods so a future shell could reuse
the same backend.

## App States

The shell should model these states explicitly:

| State | Meaning | Primary actions |
|-------|---------|-----------------|
| Needs setup | Recording or compile checks are missing | Check setup, open logs, create support bundle |
| Can record | Recorder dependencies are ready | Start recording |
| Recording | Recorder process or lock file is active | Stop/open tray guidance, show active status |
| Review | A completed recording is selected | Preview, redact, exclude, export, compile |
| Compiling | Agent SDK compile is running | Show progress/logs, prevent conflicting actions |
| Saved | Skill generation completed | Open skill, open folder, compile another |

Setup state should stay visible even after the user reaches the Review screen.
For example, a user may be able to record but unable to compile because the
Agent SDK is missing.

## Primary UI

The first version should use a work-focused desktop layout:

- Left sidebar: app state, setup status, recent recordings.
- Main review area: selected recording summary, screenshot preview, event
  timeline, and privacy warnings.
- Right/details area: selected event details, screenshot frame metadata,
  inclusion/redaction controls, compile readiness.
- Bottom/status area: runtime messages, current recording/compile status, link
  to logs.

The app should avoid a marketing-style landing page. The first screen should be
the working app.

## Review Model

The review layer should introduce an explicit model separate from raw JSONL:

| Entity | Purpose |
|--------|---------|
| RecordingReview | Summary of a recording plus editable review state |
| ReviewEvent | One parsed JSONL event plus include/exclude status |
| ReviewFrame | One screenshot frame plus include/exclude status |
| Redaction | A rectangular overlay or full-frame suppression marker |
| CompileSelection | The final filtered set sent to the compiler |

Review data should be saved beside the recording as `review.json`, so users can
leave and return without losing edits.

Minimum review actions:

- Exclude an event from compile.
- Exclude a screenshot frame from compile.
- Mark a screenshot as sensitive.
- Show privacy warnings for sensitive-window suppression already captured by the
  recorder.

Later review actions:

- Draw rectangular redactions on screenshots.
- Edit or redact clipboard text.
- Add human notes or narration transcript.
- Undo/redo review edits.

## Recorder And Tray Ownership

The first Qt version should not mix two independent tray/status owners.

Short term:

- Keep the existing recorder process and `pystray` tray behavior.
- Qt shell launches the recorder and detects active recording through the
  existing lock/status file behavior.
- Qt shell shows clear guidance that stopping is currently done from the tray.

Medium term:

- Move tray ownership into Qt or create a small IPC contract so the shell can
  start, stop, and observe recording state reliably.
- Avoid having both `pystray` and Qt independently claim control of the same
  recording lifecycle.

## Compile Flow

The compile action should be available only from the Review screen.

Before compile:

- Run setup checks.
- Confirm Agent SDK readiness.
- Confirm no recording is active.
- Build the compile selection from review state.

For the first version, compilation may still open or stream through a subprocess
if needed. The UI should show that compile is running and direct the user to the
visible prompt/output. Later, compile progress and generated skill review should
move fully into the Qt app.

## Packaging Spike

Before fully replacing Tkinter, build a small PySide6 packaging spike.

The spike must verify:

- PySide6 app launches on Windows.
- It can import or call current app services.
- It can list recordings and render screenshot thumbnails.
- It can start the recorder subprocess.
- It can run setup checks.
- PyInstaller can bundle the shell.
- Inno Setup can package the bundled app.
- Installer size, cold start, and Windows 10/11 behavior are acceptable.

The spike should also fix the known packaging risks:

- Use the correct `src` import path in the PyInstaller spec.
- Delete only known build outputs instead of the whole repo `dist/` tree.

## Testing

Unit tests:

- Review model parsing and persistence.
- Include/exclude filtering.
- Compile selection generation.
- Recorder process service state transitions.
- Setup-state mapping for the UI.

Integration tests:

- Qt shell can start in check-only/headless-safe mode.
- Recordings list loads from fixture folders.
- Review state persists and reloads.
- Compile command receives the filtered recording selection.

Windows smoke tests:

- Install from Git checkout with `install.bat`.
- Launch Qt app.
- Start a recording.
- Stop from tray or supported stop path.
- Review screenshots/events.
- Exclude a frame/event.
- Compile or verify compile setup failure is clear.
- Open logs and create support bundle.

## Risks And Mitigations

| Risk | Mitigation |
|------|------------|
| PySide6 increases installer size and packaging complexity | Run packaging spike before full migration |
| Qt and `pystray` duplicate recording state | Keep recorder as subprocess first; define one owner before deeper integration |
| Review UI becomes too shallow | Define review model before visual polish |
| Cross-platform promise is overstated | Describe as Windows-first with portable UI architecture |
| Future shell replacement becomes hard | Keep backend services shell-neutral |

## Acceptance Criteria

- A user can launch the modern shell and immediately understand current setup
  and recording state.
- A user can select a completed recording and inspect its screenshots/events.
- A user can exclude at least one event or frame before compile.
- A user can start the compile path only after review.
- Logs and support bundle actions remain visible.
- Existing CLI flows continue to work.
- The packaging spike demonstrates that PySide6 is viable on Windows.
