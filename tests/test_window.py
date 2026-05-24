from teach_skill.recorder.window import WindowTracker


def test_window_tracker_initial_state():
    tracker = WindowTracker()
    assert tracker.last_process is None
    assert tracker.last_title is None


def test_window_tracker_detects_switch():
    tracker = WindowTracker()
    switched = tracker.update_active_window({"process": "chrome.exe", "title": "Google Docs"})
    assert switched is True
    assert tracker.last_process == "chrome.exe"
    
    # Switch title only
    switched_title = tracker.update_active_window({"process": "chrome.exe", "title": "YouTube"})
    assert switched_title is True
    assert tracker.last_title == "YouTube"
    
    # Same window = no switch
    switched_same = tracker.update_active_window({"process": "chrome.exe", "title": "YouTube"})
    assert switched_same is False
