import asyncio
import sys
from pathlib import Path

import click

from teach_skill import __version__
from teach_skill.compiler.agent import SkillCompiler, check_agent_sdk, save_skill


@click.group()
@click.version_option(version=__version__)
def main():
    """Teach Skill — record workflows, compile Claude Code skills."""
    pass


@main.command()
@click.argument("jsonl_path", type=click.Path(exists=True, path_type=Path))
def compile(jsonl_path: Path):
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

    if not click.confirm("Does this skill look correct?"):
        click.echo("Skill discarded. Recording is still at:")
        click.echo(f"  {jsonl_path}")
        click.echo("Re-run `teach-skill compile` to try again.")
        return

    task_name = click.prompt("Skill name (kebab-case)", type=str)

    save_global = click.confirm("Save globally? (No = save to current project)", default=True)
    skill_path = save_skill(skill_text, task_name, global_save=save_global)

    click.echo(f"Skill saved to: {skill_path}")


@main.command()
def record():
    """Start the Teach Skill recorder (Windows only)."""
    if sys.platform != "win32":
        click.echo("Error: Recording is only supported on Windows.", err=True)
        sys.exit(1)

    click.echo("Recorder not yet implemented. See Plan 2 (Windows Recorder).")
    sys.exit(1)


if __name__ == "__main__":
    main()
