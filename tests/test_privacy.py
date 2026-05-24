from teach_skill.recorder.privacy import PrivacyFilter


def test_detects_password_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Reset Password - Google Chrome") is True


def test_detects_login_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Sign in to your account - Chrome") is True


def test_detects_okta_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Okta - Single Sign-On") is True


def test_detects_azure_ad_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Azure AD - Pick an account") is True


def test_detects_duo_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Duo Security - Two-Factor Authentication") is True


def test_detects_mfa_in_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Multi-Factor Authentication Required") is True


def test_passes_normal_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Google Sheets - Q2 Report") is False


def test_passes_normal_app_title():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_title("Visual Studio Code - main.py") is False


def test_disabled_filter_passes_everything():
    pf = PrivacyFilter(enabled=False)
    assert pf.is_sensitive_title("Reset Password - Chrome") is False


def test_redact_title_replaces_sensitive():
    pf = PrivacyFilter(enabled=True)
    result = pf.redact_title("Reset Password - Chrome")
    assert result == "[auth/login - redacted]"


def test_redact_title_passes_normal():
    pf = PrivacyFilter(enabled=True)
    result = pf.redact_title("Google Sheets - Q2 Report")
    assert result == "Google Sheets - Q2 Report"


def test_sensitive_clipboard_content():
    pf = PrivacyFilter(enabled=True)
    assert pf.is_sensitive_clipboard("my_password_123") is False
    assert pf.is_sensitive_clipboard("password: secret123") is True
    assert pf.is_sensitive_clipboard("api_key=sk-abc123def456") is True


def test_disabled_filter_passes_clipboard():
    pf = PrivacyFilter(enabled=False)
    assert pf.is_sensitive_clipboard("password: secret123") is False
