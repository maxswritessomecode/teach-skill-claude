class InputCounter:
    def __init__(self):
        self.click_count = 0
        self.keystroke_count = 0

    def on_click(self, x, y, button, pressed):
        if pressed:
            self.click_count += 1

    def on_press(self, key):
        self.keystroke_count += 1

    def reset(self) -> tuple[int, int]:
        clicks = self.click_count
        keys = self.keystroke_count
        self.click_count = 0
        self.keystroke_count = 0
        return clicks, keys
