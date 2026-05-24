from teach_skill.recorder.clipboard import ClipboardMonitor
from teach_skill.recorder.privacy import PrivacyFilter


def test_clipboard_monitor_detects_changes():
    monitor = ClipboardMonitor(privacy_filter=PrivacyFilter(enabled=True))
    assert monitor.update_content("test") == "test"
    # Same content = no change detected
    assert monitor.update_content("test") is None
    # Sensitive content = redacted
    assert monitor.update_content("password = secret123") is None
