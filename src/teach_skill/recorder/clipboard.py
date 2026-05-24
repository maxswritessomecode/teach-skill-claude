from teach_skill.recorder.privacy import PrivacyFilter


class ClipboardMonitor:
    def __init__(self, privacy_filter: PrivacyFilter):
        self.privacy_filter = privacy_filter
        self.last_text = ""

    def update_content(self, text: str) -> str | None:
        if not text or text == self.last_text:
            return None
        
        self.last_text = text
        if self.privacy_filter.is_sensitive_clipboard(text):
            return None
            
        return text
