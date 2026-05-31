# Smoother Windows Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make install, record, compile, and save usable without asking low-entry Windows users to operate PowerShell directly.

**Architecture:** Keep the current CLI and PowerShell scripts as internal plumbing, then add a small Python launcher and a reusable doctor layer. The launcher exposes simple app states, recent recordings, compile actions, and export/open-folder actions while the doctor gives clear readiness outcomes.

**Tech Stack:** Python, Click, Tkinter from the standard library, pytest, Windows `.ps1`/`.bat` launcher scripts.

---

### Task 1: Doctor Core

**Files:**
- Create: `src/teach_skill/doctor.py`
- Modify: `src/teach_skill/cli.py`
- Test: `tests/test_doctor.py`

- [ ] Write tests for `DoctorResult` summaries: `Ready`, `Can record, but cannot compile yet`, and `Needs setup`.
- [ ] Write tests for dependency checks by injecting fake command/import/path probes.
- [ ] Implement `teach_skill.doctor` with structured checks for Python, config folder, recordings folder, Claude Code, and Agent SDK.
- [ ] Add `teach-skill doctor` CLI output that prints one primary status and individual check lines.
- [ ] Run `tests/test_doctor.py`.

### Task 2: Launcher State Model

**Files:**
- Create: `src/teach_skill/launcher_state.py`
- Test: `tests/test_launcher_state.py`

- [ ] Write tests for listing recent recording folders from `config["storage_path"]`.
- [ ] Write tests for identifying recordings with `recording.jsonl`, frame counts, and newest-first order.
- [ ] Implement pure state helpers used by the GUI.
- [ ] Run `tests/test_launcher_state.py`.

### Task 3: Launcher UI And CLI

**Files:**
- Create: `src/teach_skill/launcher.py`
- Modify: `src/teach_skill/cli.py`
- Test: `tests/test_cli_record.py`

- [ ] Add a CLI test that `teach-skill launch --check-only` runs doctor checks without opening a GUI.
- [ ] Implement a Tkinter launcher with buttons for Start Recording, Compile Latest, Open Recordings, Export Latest, and Check Setup.
- [ ] Keep subprocess calls isolated behind helper functions so the GUI remains thin.
- [ ] Run launcher-related tests.

### Task 4: Installer And Docs

**Files:**
- Modify: `install.ps1`
- Modify: `README.md`
- Test: `tests/test_windows_scripts.py`

- [ ] Write script tests asserting the desktop launcher starts `teach_skill.cli launch`, not direct recording.
- [ ] Update `install.ps1` to create a `Start Teach Skill Claude.bat` launcher for the app.
- [ ] Update README beginner flow to describe double-click launcher, setup check, record, review, compile, export.
- [ ] Run script and docs-related tests.

### Task 5: Full Verification

**Files:**
- All changed files

- [ ] Run `.venv/bin/python -m pytest -q`.
- [ ] Run code review and QA gates.
- [ ] Report branch name, changed files, and verification results.
