# Recording Management Controls Design

## Purpose

Make the Qt shell practical for real recording sessions by letting users name, delete, pause, and resume recordings without leaving the app.

## Scope

This change adds:

- Friendly names for completed recordings.
- Delete controls for completed recordings in the recent recordings list.
- Pause and resume controls for the active recording.
- Safety checks that prevent destructive actions against an active recording folder.

This change does not add active-recording discard/restart. That is a separate workflow because it combines stop, delete, and optional restart.

## Friendly Names

Recording folders keep their timestamp-based folder names. The app stores a user-facing title in `recording-info.json` inside the recording folder.

The recent recordings list displays the friendly name when present, with the folder name still available in the tooltip/path. This avoids breaking existing file paths, compile behavior, exports, and support bundles.

## Delete

Users can delete the selected completed recording from the recent recordings list after confirmation. Delete removes the entire recording folder.

The app blocks delete when a recording is active and the selected recording is under the active recordings root. The first version does not try to detect the exact active session folder, because the current cross-process state only exposes the root-level active lock. This conservative behavior avoids deleting files while the recorder process may still be writing.

## Pause And Resume

Pause applies to the active recorder process and captures nothing while paused:

- no screenshots
- no clicks
- no keystrokes
- no clipboard text
- no window switches

Resume continues in the same recording folder.

The GUI communicates pause/resume through root-level control files next to the existing stop request file. The recorder tray polls those controls and updates the controller state. The recorder writes lightweight `recording_paused` and `recording_resumed` events so the compiler can see an intentional gap, but no user activity during the pause is captured.

## UI

The Qt sidebar adds Pause/Resume near Start/Stop. The recent recordings list adds Rename and Delete actions for the selected recording.

Buttons are enabled from app state:

- Start: enabled when setup can record and no active recording is running.
- Stop: enabled when recording is active.
- Pause: enabled when recording is active and not paused.
- Resume: enabled when recording is active and paused.
- Rename/Delete: enabled when a completed recording is selected and no active recording blocks list mutation.

## Testing

Tests cover:

- friendly metadata read/write and safe title validation
- delete selected recording with active-recording block
- pause/resume request files
- recorder controller ignoring events while paused
- tray polling applying pause/resume
- Qt service methods for rename/delete/pause/resume
- Qt window handlers calling services and refreshing state

Manual Windows smoke should verify Qt Start -> Pause -> Resume -> Stop, that no pause activity is captured, and that rename/delete work from the recent recordings list.
