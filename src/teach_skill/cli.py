import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click

from teach_skill import __version__
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk, save_skill
from teach_skill.config import load_config
from teach_skill.diagnostics import create_support_bundle
from teach_skill.doctor import format_doctor_result, run_doctor
from teach_skill.runtime_log import configure_logging, get_logger, log_path



@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """Teach Skill Claude - record workflows, compile Claude Code skills."""
    command = ctx.invoked_subcommand or "root"
    configure_logging(command)


@main.command()
@click.argument("jsonl_path", type=click.Path(exists=True, path_type=Path))
@click.option("--yes", "-y", is_flag=True, help="Auto-approve the generated skill and save it without prompting.")
@click.option("--name", "-n", type=str, help="Specify the skill name for auto-saving.")
@click.option("--global/--local", "save_global", default=True, help="Save globally (default) or locally to current project.")
def compile(jsonl_path: Path, yes: bool, name: str, save_global: bool):
    """Compile a JSONL recording into a Claude Code skill."""
    logger = get_logger("cli")
    logger.info("compile requested path=%s", jsonl_path)
    if not check_agent_sdk():
        logger.error("compile failed missing_agent_sdk")
        click.echo("Error: claude-agent-sdk not installed.", err=True)
        click.echo("Run: pip install claude-agent-sdk", err=True)
        sys.exit(1)

    config = load_config()
    recordings_root = Path(config.get("storage_path", str(Path.home() / ".teach-skill" / "recordings"))).resolve()
    try:
        jsonl_path.resolve().relative_to(recordings_root)
        from teach_skill.recorder.lock import is_recording_active

        if is_recording_active(recordings_root):
            logger.warning("compile blocked active_recording path=%s", jsonl_path)
            click.echo("Error: Stop the active recording before compiling a skill.", err=True)
            sys.exit(1)
    except ValueError:
        pass

    compiler = SkillCompiler(
        jsonl_path,
        compile_max_image_edge=config.get("compile_max_image_edge", 1568),
    )

    click.echo(f"Loading recording: {jsonl_path}")
    compiler.load()

    rec = compiler.recording
    click.echo(f"  Machine: {rec.meta.get('machine', 'unknown')}")
    click.echo(f"  Events: {len(rec.events)}")
    click.echo(f"  Screenshots: {len(rec.screenshot_paths)}")
    click.echo()

    click.echo("Compiling skill via Agent SDK...")
    try:
        skill_text = asyncio.run(compiler.compile())
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo()
    click.echo("=" * 60)
    click.echo("GENERATED SKILL")
    click.echo("=" * 60)
    click.echo(skill_text)
    click.echo("=" * 60)
    click.echo()

    if not yes:
        if not click.confirm("Does this skill look correct?"):
            click.echo("Skill discarded. Recording is still at:")
            click.echo(f"  {jsonl_path}")
            click.echo("Re-run `teach-skill compile` to try again.")
            return

        task_name = click.prompt("Skill name (kebab-case)", type=str)
        save_global = click.confirm("Save globally? (No = save to current project)", default=True)
    else:
        if not name:
            # Fallback to the directory name or a default
            name = jsonl_path.parent.name
            if name.startswith("recording_"):
                name = name.replace("recording_", "skill-")
            name = name.replace("_", "-")
        task_name = name

    skill_path = save_skill(skill_text, task_name, global_save=save_global)

    logger.info("skill saved path=%s", skill_path)
    click.echo(f"Skill saved to: {skill_path}")


@main.command()
@click.option("--check-only", is_flag=True, help="Run setup checks without opening the launcher window.")
@click.option("--qt", "use_qt", is_flag=True, help="Open the PySide6 Record And Review shell.")
def launch(check_only: bool, use_qt: bool):
    """Open the guided Teach Skill Claude launcher."""
    logger = get_logger("cli")
    result = run_doctor()
    logger.info("launch requested check_only=%s qt=%s status=%s", check_only, use_qt, result.status)
    for line in format_doctor_result(result):
        click.echo(line)

    if check_only:
        return

    if use_qt:
        from teach_skill.qt_app.app import launch_qt_app

        launch_qt_app()
        return

    from teach_skill.launcher import launch_app

    launch_app()


@main.command()
def doctor():
    """Check whether Teach Skill Claude is ready to record and compile."""
    result = run_doctor()
    get_logger("cli").info("doctor status=%s", result.status)
    for line in format_doctor_result(result):
        click.echo(line)


@main.command()
def logs():
    """Show the Teach Skill Claude log file path."""
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    get_logger("cli").info("logs path requested path=%s", path)
    click.echo(f"Log file: {path}")


@main.command("support-bundle")
def support_bundle():
    """Create a support bundle with diagnostics and logs."""
    bundle_path = create_support_bundle()
    get_logger("cli").info("support bundle created path=%s", bundle_path)
    click.echo(f"Support bundle saved to: {bundle_path}")



@main.command()
@click.option("--test-mode", is_flag=True, hidden=True)
@click.option("--auto-compile", is_flag=True, help="Automatically compile the recording into a skill when stopped.")
def record(test_mode: bool, auto_compile: bool):
    """Start the Teach Skill Claude recorder (Windows only)."""
    logger = get_logger("cli")
    if sys.platform != "win32" and not test_mode:
        logger.error("record blocked unsupported_platform platform=%s", sys.platform)
        click.echo("Error: Recording is only supported on Windows.", err=True)
        click.echo("Run this command on a Windows 10 or Windows 11 computer.", err=True)
        sys.exit(1)

    config = load_config()
    recordings_root = Path(config.get("storage_path", str(Path.home() / ".teach-skill" / "recordings")))
    from teach_skill.recorder.lock import RecorderLock, RecordingAlreadyRunning
    from teach_skill.recorder.control import (
        clear_pause_request,
        clear_resume_request,
        clear_stop_request,
        mark_recording_resumed,
    )

    try:
        with RecorderLock(recordings_root):
            clear_pause_request(recordings_root)
            clear_resume_request(recordings_root)
            clear_stop_request(recordings_root)
            mark_recording_resumed(recordings_root)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            session_dir = recordings_root / f"recording_{timestamp}"
            session_dir.mkdir(parents=True, exist_ok=False)
            logger.info("recording started session_dir=%s", session_dir)

            click.echo("Starting recorder session...")
            click.echo("Telemetry log and frames will be saved to:")
            click.echo(f"  {session_dir}")
            click.echo()
            click.echo("System Tray Icon created. Use the menu option to stop recording.")
            click.echo("Please grant Windows permissions if requested.")

            from teach_skill.recorder.writer import EventWriter
            from teach_skill.recorder.controller import RecorderController
            from teach_skill.recorder.tray import RecorderTrayApp

            writer = EventWriter(session_dir)
            controller = RecorderController(writer, config)
            app = RecorderTrayApp(controller, recordings_root=recordings_root)
            app.start()
            clear_pause_request(recordings_root)
            clear_resume_request(recordings_root)
            clear_stop_request(recordings_root)
            mark_recording_resumed(recordings_root)

            if auto_compile:
                jsonl_path = session_dir / "recording.jsonl"
                click.echo("\n[+] Recording stopped. Auto-compiling skill...")
                if not check_agent_sdk():
                    click.echo("Error: claude-agent-sdk is not installed on this machine.", err=True)
                    click.echo("Please install it to use --auto-compile: pip install claude-agent-sdk", err=True)
                    sys.exit(1)

                compiler = SkillCompiler(
                    jsonl_path,
                    compile_max_image_edge=config.get("compile_max_image_edge", 1568),
                )

                click.echo("Compiling skill via Agent SDK...")
                try:
                    skill_text = asyncio.run(compiler.compile())
                    task_name = session_dir.name.replace("recording_", "skill-").replace("_", "-")
                    skill_path = save_skill(skill_text, task_name, global_save=True)
                    logger.info("auto compile saved path=%s", skill_path)
                    click.echo(f"[✓] Skill compiled and saved globally to: {skill_path}")
                except Exception as e:
                    logger.exception("auto compile failed")
                    click.echo(f"Error compiling skill: {e}", err=True)
    except RecordingAlreadyRunning:
        logger.warning("record blocked active_recording")
        click.echo("Error: Another recording appears to be running.", err=True)
        click.echo("Stop the active recording before starting a new one.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
