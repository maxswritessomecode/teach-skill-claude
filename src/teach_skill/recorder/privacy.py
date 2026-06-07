import re

SENSITIVE_TITLE_PATTERNS = [
    r"password",
    r"sign[\s\-_]?in",
    r"log[\s\-_]?in",
    r"credentials",
    r"okta",
    r"azure[\s\-_]?ad",
    r"duo[\s\-_]?security",
    r"onelogin",
    r"auth0",
    r"multi[\s\-_]?factor",
    r"verify your identity",
    r"two[\s\-_]?factor",
    r"authentication",
    r"sso",
    r"\bbank\b",
]

SENSITIVE_CLIPBOARD_PATTERNS = [
    r"password\s*[:=]",
    r"api[_\-]?key\s*[:=]",
    r"secret\s*[:=]",
    r"token\s*[:=]",
    r"bearer\s+\S+",
]

_title_regex = re.compile("|".join(SENSITIVE_TITLE_PATTERNS), re.IGNORECASE)
_clipboard_regex = re.compile("|".join(SENSITIVE_CLIPBOARD_PATTERNS), re.IGNORECASE)


class PrivacyFilter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def is_sensitive_title(self, title: str) -> bool:
        if not self.enabled:
            return False
        return bool(_title_regex.search(title))

    def redact_title(self, title: str) -> str:
        if self.is_sensitive_title(title):
            return "[auth/login - redacted]"
        return title

    def redact_ui_text(self, text: str) -> str:
        if not self.enabled:
            return _compact_text(text)
        compact = _compact_text(text)
        if _title_regex.search(compact) or _clipboard_regex.search(compact):
            return "[redacted]"
        return compact

    def is_sensitive_clipboard(self, text: str) -> bool:
        if not self.enabled:
            return False
        return bool(_clipboard_regex.search(text))


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()[:160]
