# Teach Skill — Design Decisions Log

## D1: User trigger model
**Question:** How does the user signal "I'm done, compile the skill"?
| Option | Description |
|--------|-------------|
| 1. Hotkey | Key combo (e.g., Ctrl+Shift+T) to start/stop recording |
| 2. Tray menu | Right-click system tray → Start/Stop & Compile |
| **3. Both** | **Tray menu for discovery, hotkey for power users** |
**Decision:** Option 3 — Both

## D2: Telemetry scope
**Question:** What telemetry should the POC capture?
| Option | Description |
|--------|-------------|
| 1. Minimal | Window title + process name only |
| **2. Standard + screenshots** | **Window title + process name + click counts + keystroke frequency + screenshots** |
| 3. Full | Above + audio narration |
**Decision:** Option 2 with screenshots added — standard telemetry plus visual capture

## D3: Screenshot trigger
**Question:** When should screenshots be captured?
| Option | Description |
|--------|-------------|
| 1. On window switch | Snap screenshot each time foreground app changes |
| 2. Window switch + timed interval | Above + every N seconds within same window |
| 3. On significant events | Window switch + after click/keystroke bursts settle |
**Decision:** Option 1 + input-driven supplement. Window-switch screenshots remain primary. Added: capture on click if 5+ seconds since last screenshot, to cover single-app workflows (e.g., multi-step Salesforce sequence). Revised after Gemini review identified blind spot.

## D4: Agent SDK integration
**Question:** How does telemetry get to the Agent SDK for compilation?
| Option | Description |
|--------|-------------|
| 1. Shell out to Claude CLI | Tray app invokes `claude` with telemetry file as context |
| **2. Agent SDK as Python library** | **Import `claude-agent-sdk`, build agent that processes telemetry in-process** |
| 3. Export + manual handoff | Save telemetry file, user feeds to Claude Code manually |
**Decision:** Option 2 — Agent SDK as Python library. No API key needed (uses existing Claude Code subscription auth). Clean programmatic API with native image support. Avoids brittle CLI subprocess parsing. Revised after Gemini review flagged CLI brittleness and research confirmed Agent SDK auth works via subscription.

## D5: Skill output format
**Question:** What should the generated skill look like?
| Option | Description |
|--------|-------------|
| 1. Single SKILL.md | One file with skill description, triggers, and steps |
| 2. SKILL.md + supporting files | Skill file plus templates, checklists, reference data |
| **3. SKILL.md + validation prompt** | **Generate skill, show to user for review/editing before saving** |
**Decision:** Option 3 — Human-in-the-loop review before saving to skills directory. Claude CLI interaction makes this natural.

## D6: Skill save location
**Question:** Where should the finished skill be saved?
| Option | Description |
|--------|-------------|
| 1. Global skills directory | `%USERPROFILE%\.claude\skills\<task_name>\SKILL.md` — available across all projects |
| 2. Current project `.claude/` | `.claude\skills\<task_name>\SKILL.md` — scoped to that project |
| **3. User chooses at review time** | **Prompt asks "save globally or to this project?" — default to global** |
**Decision:** Option 3 — User picks at review time. Covers both consultant (project-scoped) and individual (global) use cases.

## D7: Telemetry storage during recording
**Question:** How should telemetry be stored during recording?
| Option | Description |
|--------|-------------|
| 1. In-memory only | Python list, dump to JSON on stop. Data lost on crash. |
| **2. Append-to-file streaming** | **JSONL file, each event written as it happens. Crash-resilient.** |
| 3. SQLite | Structured DB. Queryable but overkill for linear timeline POC. |
**Decision:** Option 2 — JSONL streaming. Crash-resilient and directly consumable by Claude CLI.

## D8: Installation story
**Question:** What's the installation story for end users?
| Option | Description |
|--------|-------------|
| 1. `pip install teach-skill` | Publish to PyPI. Clean but requires Python on target. |
| 2. Single `.exe` bundle | PyInstaller package. Zero-friction but heavier build step. |
| **3. Git clone + pip install** | **Clone repo, install from source. Fast to ship for POC.** |
**Decision:** Option 3 — Clone + install for POC. Option 2 (.exe) is the future distribution goal once concept is validated.

## D9: Architecture approach
**Question:** Overall system architecture?
| Option | Description |
|--------|-------------|
| 1. Monolithic single-process | Everything in threads within one app |
| **2. Two-process split** | **Recorder (tray + telemetry → JSONL) and Compiler (JSONL → Claude CLI → SKILL.md)** |
| 3. Plugin architecture | Core event bus with pluggable collectors |
**Decision:** Option 2 — Two-process split. Clean separation, compiler can run independently on existing JSONL files, isolates tray app from Claude CLI call.

## D10: Screenshot format
**Question:** What image format for screenshots?
| Option | Description |
|--------|-------------|
| **1. PNG** | **Lossless, crisp text/UI. ~200-500KB per shot. Best for Claude readability.** |
| 2. JPEG (85-90%) | Smaller files but compression artifacts blur text |
| 3. WebP lossless | ~30% smaller than PNG but less universal tooling |
**Decision:** Option 1 — PNG. Screenshots are text/UI which JPEG handles worst. Claude needs to read window contents clearly.

## D11: Privacy / sensitive input handling
**Question:** How to handle password fields and sensitive input during recording?
| Option | Description |
|--------|-------------|
| 1. Auto-detect + suppress screenshots | Win32 API password field detection, skip screenshot. Can't detect web-based fields. |
| 2. Manual pause hotkey | User presses hotkey to pause for sensitive moments |
| **3. Hybrid + capture-all toggle** | **Auto-detect + manual pause + title filtering, with a Settings toggle to disable all filtering** |
| 4. Post-recording scrub | Analyze and redact after recording stops |
**Decision:** Option 3 with a "capture everything" toggle in Settings for environments where sensitivity isn't a concern. Three detection layers: (1) Win32 password field detection for native apps, (2) regex title filtering for sensitive keywords, (3) SSO/auth provider detection (Okta, Azure AD, Duo, OneLogin, Auth0, etc.). Plus Ctrl+Shift+P manual pause hotkey. All layers bypass-able via Settings → Privacy Filter → Off.

## D12: Clipboard capture (from Gemini review)
**Decision:** Add text-only clipboard change capture as a new event type. Routed through privacy filter. High-signal context for understanding why the user switched windows. New JSONL event: `{"type": "clipboard_text", "content": "...", "source_process": "..."}`.

## D13: Screenshot resolution (from Gemini review)
**Decision:** Capture at native resolution. Compiler resizes before sending to Claude. Avoids HiDPI/4K scaling making text unreadable at 1280px.

## D14: Prompt strategy (from Gemini review)
**Decision:** System prompt instructs Claude to treat screenshots as primary source of truth for the workflow sequence, using JSONL timeline as timestamps and structural markers. Compensates for sparse telemetry text (no raw keystrokes/coordinates).
