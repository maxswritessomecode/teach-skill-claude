# Generic Action Capture Design

## Purpose

Improve recording fidelity for formatting, selection, shortcuts, and app interactions across desktop and web apps. The recorder should not be Excel-specific. It should capture generic intent signals that help the compiler understand work in Excel, Word, PowerPoint, browsers, and other applications.

## Scope

This change adds:

- Keyboard shortcut events such as `ctrl+b`, `ctrl+s`, and multi-key modifier chords.
- Mouse drag/selection events with start/end coordinates.
- Post-action screenshots after clicks, shortcuts, and drag release.
- Privacy-aware typed text support through the existing `capture_raw_keystrokes` config.

This change does not add app-specific document inspection. Excel workbook, Word document, PowerPoint deck, and browser DOM enrichment remain later optional layers.

## Capture Model

The recorder emits structured events for user intent:

- `keyboard_shortcut`: modifier chord pressed while a non-modifier key is pressed.
- `drag_select`: mouse press, movement, and release over a meaningful distance.
- `post_action_capture`: screenshot shortly after a click, shortcut, or drag release.

Typed formulas/text are only included when `capture_raw_keystrokes` is enabled and the active window is not privacy-sensitive. Existing privacy redaction rules continue to apply.

## Screenshot Timing

The recorder captures a screenshot shortly after meaningful actions. This captures visual after-state, such as bold text, cell fill color, borders, selected ranges, menu state, or changed web UI.

The first implementation captures synchronously when the action event is handled. A later version can add a short delayed capture worker if Windows UI timing needs it.

## Privacy

Shortcut names and drag coordinates are captured by default because they do not reveal typed secrets. Raw typed text stays opt-in through config. Sensitive window titles suppress screenshots and raw detail, as they do today.

## Testing

Tests cover:

- shortcut detection without requiring raw text capture
- typed text still gated by `capture_raw_keystrokes`
- drag selection events
- post-action screenshots after clicks, shortcuts, and drags
- paused recordings ignore shortcuts, typing, clicks, and drags
