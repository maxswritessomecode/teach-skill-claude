# Teach Skill Claude Roadmap

This is a working tally of product ideas and implementation directions. It is
not a commitment to build everything in this order.

## Near Term

### Windows Install And First Run

- Keep the advanced `install.bat` path working for Git checkout testing.
- Build a real Full Installer path for normal Windows users.
- Bundle the Python runtime and recorder dependencies in the Full Installer.
- Decide whether `claude-agent-sdk` is bundled or left as a separate compile-time dependency.
- Keep recording usable even when Claude Code or compile dependencies are not ready.
- Add real Windows smoke tests for install, launcher, tray, recording, compile, export, logs, and support bundle.

### Windows App UX

- Replace the bare launcher with a clearer state-driven UI.
- Show setup states: `Needs setup`, `Can record`, `Can compile`, `Ready`.
- Show recording states: `Idle`, `Recording`, `Review`, `Compiling`, `Saved`.
- Add a recent recordings list with open, compile, export, and delete actions.
- Add visible buttons for logs, support bundle, and setup checks.
- Make active recording status obvious.

### Diagnostics

- Keep runtime logs under `%USERPROFILE%\.teach-skill\logs`.
- Keep support bundles separate from recordings and screenshots.
- Treat support bundles as sensitive because logs may include local paths.
- Make support bundles useful for diagnosing install, dependency, Claude Code, Agent SDK, and recorder failures.

## Mid Term

### Voice Narration

- Add optional microphone narration while recording a workflow.
- Transcribe narration after recording stops.
- Save transcript beside `recording.jsonl`.
- Let the user review and redact the transcript before compile.
- Feed transcript context into the skill compiler along with screenshots and events.
- Avoid live agent coaching at first; start with narration as context.

### Review Before Compile

- Add a review screen before compiling a skill.
- Show recording summary, screenshots count, apps/windows touched, transcript, and privacy warnings.
- Let users remove or redact sensitive parts before compiling.
- Make compile output easier to inspect before saving.

### Skill Chains

- Support workflows made of reusable skill blocks.
- Each skill block should define inputs, outputs, preconditions, validation, recovery, and optional human checkpoints.
- Example chain:
  - Parse a source file.
  - Validate extracted fields.
  - Open Excel and run a cloud/plugin task.
  - Save/export workbook.
  - Open PowerPoint and create or update a deck.
  - Validate slides.
- Use the best tool per step: Python parsing, APIs, desktop automation, browser automation, or human checkpoint.

### Workflow Format

- Add a simple `workflow.yaml` or `workflow.json` format.
- Represent steps, inputs, outputs, checkpoints, and failure behavior.
- Start with a simple runner before building a full visual workflow editor.

## Later

### Update Mechanism

- Full Installer path should update from GitHub Releases.
- Advanced Git checkout path can update with `git pull`.
- Avoid making Git the default update mechanism for nontechnical users.
- Later, consider signed installer auto-update or update prompts.

### Packaging And Release

- Build Windows app bundle with PyInstaller or Nuitka.
- Build `TeachSkillClaudeSetup.exe` with Inno Setup or WiX.
- Code sign the installer and application.
- Later, add MSI for enterprise deployment if IT teams need Intune, Group Policy, repair/uninstall semantics, or managed rollout.

### Enterprise Readiness

- Document supported Windows versions and unsupported locked-down environments.
- Add privacy/admin guidance for workplace use.
- Add clearer permission explanations for screenshots, input capture, and microphone recording.
- Add repeatable Windows release validation.

## Open Questions

- Should the Agent SDK be bundled with the Full Installer, or should compile setup remain external?
- What is the minimum viable review UI before users trust generated skills?
- Which speech-to-text path should be used for narration: local, cloud, or user-configurable?
- What is the first useful Skill Chain example to build and test end-to-end?
- What support boundary should we set for corporate-managed Windows machines?
