class WindowTracker:
    def __init__(self):
        self.last_process = None
        self.last_title = None

    def update_active_window(self, current_info: dict) -> bool:
        process = current_info.get("process")
        title = current_info.get("title")

        if process != self.last_process or title != self.last_title:
            self.last_process = process
            self.last_title = title
            return True
        
        return False
