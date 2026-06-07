from teach_skill.recorder.input import InputCounter


def test_input_counter_accumulates_clicks():
    counter = InputCounter()
    assert counter.click_count == 0
    counter.on_click(0, 0, None, True)
    counter.on_click(10, 10, None, True)
    assert counter.click_count == 2


def test_input_counter_accumulates_keys():
    counter = InputCounter()
    assert counter.keystroke_count == 0
    counter.on_press(None)
    counter.on_press(None)
    assert counter.keystroke_count == 2


def test_input_counter_reset():
    counter = InputCounter()
    counter.click_count = 5
    counter.keystroke_count = 10
    clicks, keys, text = counter.reset()
    assert clicks == 5
    assert keys == 10
    assert text == ""
    assert counter.click_count == 0
    assert counter.keystroke_count == 0


def test_input_counter_captures_raw_keys():
    from unittest.mock import MagicMock
    counter = InputCounter(capture_raw=True)
    
    key_h = MagicMock()
    key_h.char = "h"
    counter.on_press(key_h)
    
    key_e = MagicMock()
    key_e.char = "e"
    counter.on_press(key_e)
    
    counter.on_press("Key.space")
    
    key_y = MagicMock()
    key_y.char = "y"
    counter.on_press(key_y)
    
    counter.on_press("Key.backspace")
    
    clicks, keys, text = counter.reset()
    assert text == "he "
    assert keys == 5


def test_input_counter_detects_keyboard_shortcuts_without_raw_capture():
    counter = InputCounter(capture_raw=False)

    assert counter.on_press("Key.ctrl_l") is None
    shortcut = counter.on_press("b")
    counter.on_release("Key.ctrl_l")

    assert shortcut == "ctrl+b"
    clicks, keys, text = counter.reset()
    assert clicks == 0
    assert keys == 2
    assert text == ""


def test_input_counter_tracks_modifier_release():
    counter = InputCounter()

    counter.on_press("Key.ctrl_l")
    counter.on_release("Key.ctrl_l")

    assert counter.on_press("b") is None


def test_input_counter_does_not_treat_shift_printable_as_shortcut():
    counter = InputCounter(capture_raw=True)

    assert counter.on_press("Key.shift") is None
    assert counter.on_press("h") is None
    counter.on_release("Key.shift")

    clicks, keys, text = counter.reset()
    assert clicks == 0
    assert keys == 2
    assert text == "h"
