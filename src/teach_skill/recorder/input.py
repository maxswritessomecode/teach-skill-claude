class InputCounter:
    def __init__(self, capture_raw: bool = False):
        self.click_count = 0
        self.keystroke_count = 0
        self.capture_raw = capture_raw
        self.typed_buffer = []

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.click_count += 1

    def on_press(self, key):
        self.keystroke_count += 1
        
        if self.capture_raw:
            try:
                if hasattr(key, 'char') and key.char is not None:
                    self.typed_buffer.append(key.char)
                else:
                    key_str = str(key)
                    if key_str == "Key.space":
                        self.typed_buffer.append(" ")
                    elif key_str == "Key.enter":
                        self.typed_buffer.append("\n")
                    elif key_str == "Key.backspace":
                        if self.typed_buffer:
                            self.typed_buffer.pop()
            except Exception:
                pass

    def reset(self) -> tuple[int, int, str]:
        clicks = self.click_count
        keys = self.keystroke_count
        typed_text = "".join(self.typed_buffer)
        
        self.click_count = 0
        self.keystroke_count = 0
        self.typed_buffer = []
        
        return clicks, keys, typed_text

