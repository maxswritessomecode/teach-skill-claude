import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click

from teach_skill import __version__
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk, save_skill
from teach_skill.config import load_config
from teach_skill.recorder.writer import EventWriter
from teach_skill.recorder.controller import RecorderController
from teach_skill.recorder.tray import RecorderTrayApp



@click.group()
@click.version_option(version=__version__)
def main():
    """Teach Skill — record workflows, compile Claude Code skills."""
    pass


@main.command()
@click.argument("jsonl_path", type=click.Path(exists=True, path_type=Path))
@click.option("--yes", "-y", is_flag=True, help="Auto-approve the generated skill and save it without prompting.")
@click.option("--name", "-n", type=str, help="Specify the skill name for auto-saving.")
@click.option("--global/--local", "save_global", default=True, help="Save globally (default) or locally to current project.")
def compile(jsonl_path: Path, yes: bool, name: str, save_global: bool):
    """Compile a JSONL recording into a Claude Code skill."""
    if not check_agent_sdk():
        click.echo("Error: claude-agent-sdk not installed.", err=True)
        click.echo("Run: pip install claude-agent-sdk", err=True)
        sys.exit(1)

    compiler = SkillCompiler(jsonl_path)

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

    click.echo(f"Skill saved to: {skill_path}")



@main.command()
@click.option("--simulate", is_flag=True, help="Simulate recording on non-Windows platforms.")
@click.option("--auto-compile", is_flag=True, help="Automatically compile the recording into a skill when stopped.")
def record(simulate: bool, auto_compile: bool):
    """Start the Teach Skill recorder (Windows only)."""
    if sys.platform != "win32" and not simulate:
        click.echo("Error: Recording is only supported on Windows.", err=True)
        click.echo("To simulate recording on Mac/Linux, run with --simulate.", err=True)
        sys.exit(1)

    config = load_config()
    recordings_root = Path(config.get("storage_path", str(Path.home() / ".teach-skill" / "recordings")))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = recordings_root / f"recording_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    click.echo("Starting recorder session...")
    click.echo("Telemetry log and frames will be saved to:")
    click.echo(f"  {session_dir}")
    click.echo()
    click.echo("System Tray Icon created. Use the menu option to stop recording.")
    click.echo("Please grant accessibility/screen recording permissions if requested.")

    writer = EventWriter(session_dir)
    controller = RecorderController(writer, config)
    app = RecorderTrayApp(controller)
    app.start()

    if auto_compile:
        jsonl_path = session_dir / "recording.jsonl"
        click.echo("\n[+] Recording stopped. Auto-compiling skill...")
        if not check_agent_sdk():
            click.echo("Error: claude-agent-sdk is not installed on this machine.", err=True)
            click.echo("Please install it to use --auto-compile: pip install claude-agent-sdk", err=True)
            sys.exit(1)

        compiler = SkillCompiler(jsonl_path)
        
        click.echo("Compiling skill via Agent SDK...")
        try:
            skill_text = asyncio.run(compiler.compile())
            task_name = session_dir.name.replace("recording_", "skill-").replace("_", "-")
            skill_path = save_skill(skill_text, task_name, global_save=True)
            click.echo(f"[✓] Skill compiled and saved globally to: {skill_path}")
        except Exception as e:
            click.echo(f"Error compiling skill: {e}", err=True)


if __name__ == "__main__":
    main()
