import json
from pathlib import Path

from teach_skill.review import (
    CompileSelection,
    load_recording_review,
)


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )


def test_load_recording_review_lists_events_and_frames(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    jsonl_path = recording_dir / "recording.jsonl"
    write_jsonl(
        jsonl_path,
        [
            {"type": "recording_meta", "machine": "PC"},
            {"type": "window_switch", "title": "Excel", "screenshot": "frames/0001.png"},
            {"type": "click", "title": "Excel", "screenshot_frame_path": r"frames\0001.png"},
            {"type": "redacted", "screenshot": "suppressed:privacy"},
            {"type": "ignored", "screenshot": None},
        ],
    )

    review = load_recording_review(recording_dir)

    assert review.recording_dir == recording_dir
    assert review.jsonl_path == jsonl_path
    assert len(review.events) == 5
    assert len(review.frames) == 1
    assert review.frames[0].relative_path == "frames/0001.png"
    assert review.frames[0].path == recording_dir / "frames" / "0001.png"
    assert review.events[1].included is True
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False


def test_review_state_persists_event_and_frame_exclusions(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
        ],
    )

    review = load_recording_review(recording_dir)
    review.events[1].included = False
    review.frames[0].included = False
    review.frames[0].sensitive = True
    review.save()

    reloaded = load_recording_review(recording_dir)

    assert reloaded.events[1].included is False
    assert reloaded.frames[0].included is False
    assert reloaded.frames[0].sensitive is True


def test_mark_frame_sensitive_persists(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [{"type": "window_switch", "screenshot": "frames/0001.png"}],
    )

    review = load_recording_review(recording_dir)
    review.frames[0].sensitive = True
    review.frames[0].included = False
    review.save()

    reloaded = load_recording_review(recording_dir)

    assert reloaded.frames[0].sensitive is True
    assert reloaded.frames[0].included is False


def test_compile_selection_excludes_events_and_frames(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    (frames_dir / "0002.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
            {"type": "window_switch", "screenshot": "frames/0002.png"},
        ],
    )

    review = load_recording_review(recording_dir)
    review.events[2].included = False
    review.frames[1].included = False

    selection = CompileSelection.from_review(review)

    assert [event["type"] for event in selection.events] == ["recording_meta", "window_switch"]
    assert selection.frame_paths == [recording_dir / "frames" / "0001.png"]


def test_compile_selection_writes_filtered_jsonl(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
            {"type": "clipboard_text", "content": "secret"},
        ],
    )
    review = load_recording_review(recording_dir)
    review.events[2].included = False
    selection = CompileSelection.from_review(review)

    filtered_path = selection.write_filtered_jsonl(recording_dir / "reviewed-recording.jsonl")

    assert filtered_path.read_text(encoding="utf-8").count("\n") == 2
    assert "secret" not in filtered_path.read_text(encoding="utf-8")


def test_load_recording_review_rejects_unsafe_frame_paths(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "safe.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "safe", "screenshot": r"frames\safe.png"},
            {"type": "windows_drive_relative", "screenshot": r"C:secret.png"},
            {"type": "windows_drive_relative_nested", "screenshot": r"C:frames\secret.png"},
            {"type": "posix_absolute", "screenshot": "/tmp/escape.png"},
            {"type": "windows_absolute", "screenshot": r"C:\Users\martin\secret.png"},
            {"type": "unc", "screenshot": r"\\server\share\secret.png"},
            {"type": "windows_rooted", "screenshot": r"\Users\martin\secret.png"},
            {"type": "posix_traversal", "screenshot": "frames/../secret.png"},
            {"type": "windows_traversal", "screenshot": r"frames\..\secret.png"},
            {"type": "missing", "screenshot": "frames/missing.png"},
        ],
    )

    review = load_recording_review(recording_dir)

    assert [frame.relative_path for frame in review.frames] == ["frames/safe.png"]
    assert review.frames[0].path == recording_dir / "frames" / "safe.png"

    selection = CompileSelection.from_review(review)

    assert [event["type"] for event in selection.events] == ["safe", "missing"]


def test_load_recording_review_scans_alternate_frame_reference(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "safe.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {
                "type": "suppressed_then_safe",
                "screenshot": "suppressed:privacy",
                "screenshot_frame_path": "frames/safe.png",
            },
            {
                "type": "unsafe_then_safe",
                "screenshot": "../secret.png",
                "screenshot_frame_path": "frames/safe.png",
            },
        ],
    )

    review = load_recording_review(recording_dir)

    assert [frame.relative_path for frame in review.frames] == ["frames/safe.png"]

    selection = CompileSelection.from_review(review)

    assert [event["type"] for event in selection.events] == ["suppressed_then_safe"]


def test_compile_selection_omits_sensitive_included_frames(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "safe.png").write_bytes(b"fake")
    (frames_dir / "sensitive.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "safe", "screenshot": "frames/safe.png"},
            {"type": "sensitive", "screenshot": "frames/sensitive.png"},
        ],
    )

    review = load_recording_review(recording_dir)
    review.frames[1].included = True
    review.frames[1].sensitive = True

    selection = CompileSelection.from_review(review)

    assert [event["type"] for event in selection.events] == ["recording_meta", "safe"]
    assert selection.frame_paths == [recording_dir / "frames" / "safe.png"]


def test_load_recording_review_skips_malformed_jsonl_lines(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    (recording_dir / "recording.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "recording_meta"}),
                "{bad json",
                json.dumps([]),
                json.dumps({"type": "window_switch", "screenshot": "frames/0001.png"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    review = load_recording_review(recording_dir)

    assert [event.data["type"] for event in review.events] == [
        "recording_meta",
        "window_switch",
    ]
    assert [event.index for event in review.events] == [0, 1]
    assert [frame.relative_path for frame in review.frames] == ["frames/0001.png"]


def test_load_recording_review_ignores_malformed_review_json(tmp_path):
    recording_dir = tmp_path / "recording_20260602_120000"
    frames_dir = recording_dir / "frames"
    frames_dir.mkdir(parents=True)
    (frames_dir / "0001.png").write_bytes(b"fake")
    write_jsonl(
        recording_dir / "recording.jsonl",
        [
            {"type": "recording_meta"},
            {"type": "window_switch", "screenshot": "frames/0001.png"},
        ],
    )
    (recording_dir / "review.json").write_text("{bad json", encoding="utf-8")

    review = load_recording_review(recording_dir)

    assert [event.included for event in review.events] == [True, True]
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False

    (recording_dir / "review.json").write_text(
        json.dumps({"excluded_events": 1, "frames": 1}),
        encoding="utf-8",
    )

    review = load_recording_review(recording_dir)

    assert [event.included for event in review.events] == [True, True]
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False

    (recording_dir / "review.json").write_text(
        json.dumps(
            {
                "excluded_events": [True, 1],
                "frames": [
                    {
                        "relative_path": "frames/0001.png",
                        "included": "no",
                        "sensitive": "yes",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    review = load_recording_review(recording_dir)

    assert [event.included for event in review.events] == [True, False]
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False

    (recording_dir / "review.json").write_text(
        json.dumps(
            {
                "excluded_events": [],
                "frames": {
                    "frames/0001.png": {
                        "included": False,
                        "sensitive": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    review = load_recording_review(recording_dir)

    assert [event.included for event in review.events] == [True, True]
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False

    (recording_dir / "review.json").write_text("[]", encoding="utf-8")

    review = load_recording_review(recording_dir)

    assert [event.included for event in review.events] == [True, True]
    assert review.frames[0].included is True
    assert review.frames[0].sensitive is False
