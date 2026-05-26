import shutil
from pathlib import Path

from teach_skill.compiler.parser import parse_recording, Recording
from teach_skill.compiler.prompt import build_system_prompt, build_user_message


def check_agent_sdk() -> bool:
    try:
        import claude_agent_sdk
        return True
    except ImportError:
        return False


def check_claude_cli() -> bool:
    return shutil.which("claude") is not None


class SkillCompiler:
    def __init__(self, recording_path: Path):
        self.recording_path = recording_path
        self.recording: Recording | None = None

    def load(self) -> None:
        self.recording = parse_recording(self.recording_path)

    def collect_screenshot_paths(self) -> list[Path]:
        if not self.recording:
            return []
        base_dir = self.recording_path.parent
        return [base_dir / p for p in self.recording.screenshot_paths]

    def build_prompt_payload(self) -> dict:
        if not self.recording:
            raise RuntimeError("Call load() before building prompt payload")
        return {
            "system": build_system_prompt(),
            "user_message": build_user_message(self.recording),
            "screenshot_paths": [str(p) for p in self.collect_screenshot_paths()],
        }

    async def compile(self) -> str:
        if not check_agent_sdk():
            raise RuntimeError(
                "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"
            )

        self.load()
        payload = self.build_prompt_payload()

        from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

        options = ClaudeAgentOptions(
            system_prompt=payload["system"],
            max_turns=15,
        )

        skill_text_blocks = []
        async for message in query(
            prompt=payload["user_message"],
            options=options,
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        skill_text_blocks.append(block.text)

        if skill_text_blocks:
            return "".join(skill_text_blocks)

        raise RuntimeError("No text response received from Claude")


def save_skill(skill_text: str, task_name: str, global_save: bool = True) -> Path:
    if global_save:
        base = Path.home() / ".claude" / "skills" / task_name
    else:
        base = Path.cwd() / ".claude" / "skills" / task_name

    base.mkdir(parents=True, exist_ok=True)
    skill_path = base / "SKILL.md"
    skill_path.write_text(skill_text)
    return skill_path
