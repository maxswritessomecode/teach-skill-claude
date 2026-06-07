class InputCounter:
    MODIFIER_ALIASES = {
        "Key.ctrl": "ctrl",
        "Key.ctrl_l": "ctrl",
        "Key.ctrl_r": "ctrl",
        "Key.shift": "shift",
        "Key.shift_l": "shift",
        "Key.shift_r": "shift",
        "Key.alt": "alt",
        "Key.alt_l": "alt",
        "Key.alt_r": "alt",
        "Key.cmd": "cmd",
        "Key.cmd_l": "cmd",
        "Key.cmd_r": "cmd",
    }
    MODIFIER_ORDER = ("ctrl", "shift", "alt", "cmd")

    def __init__(self, capture_raw: bool = False):
        self.click_count = 0
        self.keystroke_count = 0
        self.capture_raw = capture_raw
        self.typed_buffer = []
        self.active_modifiers = set()

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.click_count += 1

    def on_press(self, key):
        self.keystroke_count += 1
        key_name = self._key_name(key)
        modifier = self.MODIFIER_ALIASES.get(key_name)
        if modifier:
            self.active_modifiers.add(modifier)
            return None

        if self._is_shortcut_keypress(key_name):
            modifiers = [
                active
                for active in self.MODIFIER_ORDER
                if active in self.active_modifiers
            ]
            return "+".join([*modifiers, key_name])

        if self.capture_raw:
            try:
                if hasattr(key, 'char') and key.char is not None:
                    self.typed_buffer.append(key.char)
                elif len(key_name) == 1:
                    self.typed_buffer.append(key_name)
                elif key_name == "Key.space":
                    self.typed_buffer.append(" ")
                elif key_name == "Key.enter":
                    self.typed_buffer.append("\n")
                elif key_name == "Key.backspace":
                    if self.typed_buffer:
                        self.typed_buffer.pop()
            except Exception:
                pass
        return None

    def on_release(self, key):
        modifier = self.MODIFIER_ALIASES.get(self._key_name(key))
        if modifier:
            self.active_modifiers.discard(modifier)

    def reset(self) -> tuple[int, int, str]:
        clicks = self.click_count
        keys = self.keystroke_count
        typed_text = "".join(self.typed_buffer)
        
        self.click_count = 0
        self.keystroke_count = 0
        self.typed_buffer = []
        self.active_modifiers = set()
        
        return clicks, keys, typed_text

    def _is_shortcut_keypress(self, key_name: str) -> bool:
        if not self.active_modifiers:
            return False
        if {"ctrl", "alt", "cmd"} & self.active_modifiers:
            return True
        return "shift" in self.active_modifiers and len(key_name) != 1

    def _key_name(self, key) -> str:
        if hasattr(key, "char") and key.char is not None:
            return str(key.char).lower()
        text = str(key)
        if len(text) == 1:
            return text.lower()
        return text
