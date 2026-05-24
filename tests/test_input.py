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
    clicks, keys = counter.reset()
    assert clicks == 5
    assert keys == 10
    assert counter.click_count == 0
    assert counter.keystroke_count == 0
