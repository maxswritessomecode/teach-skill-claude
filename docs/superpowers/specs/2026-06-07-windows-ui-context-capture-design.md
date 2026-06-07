# Windows UI Context Capture Design

## Goal

Improve recordings with Windows Accessibility/UI Automation context so skills can understand what the user clicked or targeted, especially in Office and other rich desktop apps where screenshots alone may miss intent.

## Scope

- Add optional Windows-only UI Automation context capture.
- Attach UI context to click, drag selection, keyboard shortcut, and post-action screenshot events.
- Keep recorder behavior unchanged when UI Automation is unavailable.
- Do not capture raw control values by default.

## Data Captured

Each UI context entry may include:

- `name`
- `control_type`
- `automation_id`
- `class_name`
- `bounds`
- limited `parent_path`

Sensitive windows continue to suppress detailed event data. UI context strings are compacted and passed through the existing privacy redaction rules before being saved.

## Architecture

`teach_skill.recorder.ui_context.UIContextProvider` is a small optional adapter around the Windows `uiautomation` package. The recorder controller owns event enrichment and privacy filtering, keeping platform-specific access separate from saved event policy.

The compiler parser appends short labels such as `on MenuItem "Conditional Formatting"` or `targeting Button "Bold"` to timeline text when context is present.

## Testing

Tests cover:

- click, drag, shortcut, and post-action context enrichment
- sensitive-window suppression
- timeline output with UI context labels
- provider extraction using a fake UI Automation module
- graceful no-op behavior outside Windows
