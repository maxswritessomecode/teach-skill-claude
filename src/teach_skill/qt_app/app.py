import json
import sys

from teach_skill.qt_app.services import QtAppServices
from teach_skill.review import load_recording_review


def _import_qt() -> dict:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QPushButton,
            QSplitter,
            QStatusBar,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        if exc.name and not exc.name.startswith("PySide6"):
            raise
        raise RuntimeError(
            "Install the UI extra to launch the Qt app: "
            "pip install -e .[ui,recorder]"
        ) from exc

    return {
        "Qt": Qt,
        "QTimer": QTimer,
        "QPixmap": QPixmap,
        "QApplication": QApplication,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QListWidget": QListWidget,
        "QListWidgetItem": QListWidgetItem,
        "QMainWindow": QMainWindow,
        "QPushButton": QPushButton,
        "QSplitter": QSplitter,
        "QStatusBar": QStatusBar,
        "QTextEdit": QTextEdit,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
    }


def launch_qt_app() -> int:
    qt = _import_qt()
    app = qt["QApplication"].instance() or qt["QApplication"](sys.argv)
    window = TeachSkillQtWindow(qt, QtAppServices())
    window.show()
    return app.exec()


def _qt_enum(qt_namespace, name: str, group: str):
    if hasattr(qt_namespace, name):
        return getattr(qt_namespace, name)
    return getattr(getattr(qt_namespace, group), name)


class TeachSkillQtWindow:
    def __init__(self, qt: dict, services: QtAppServices):
        self.qt = qt
        self.services = services
        self.recordings = []
        self.selected_recording = None
        self.review = None
        self.current_status = None

        self.window = qt["QMainWindow"]()
        self.window.setWindowTitle("Teach Skill Claude")
        self.window.resize(1040, 680)
        self.window.setStatusBar(qt["QStatusBar"]())

        self._build_ui()
        self.refresh()
        self.status_timer = qt["QTimer"](self.window)
        self.status_timer.setInterval(1000)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start()

    def __getattr__(self, name):
        return getattr(self.window, name)

    def _build_ui(self) -> None:
        qt = self.qt
        central = qt["QWidget"]()
        layout = qt["QHBoxLayout"](central)
        splitter = qt["QSplitter"](_qt_enum(qt["Qt"], "Horizontal", "Orientation"))
        layout.addWidget(splitter)

        sidebar = qt["QWidget"]()
        sidebar_layout = qt["QVBoxLayout"](sidebar)
        self.status_label = qt["QLabel"]("Checking setup...")
        self.start_button = qt["QPushButton"]("Start Recording")
        self.stop_button = qt["QPushButton"]("Stop Recording")
        self.refresh_button = qt["QPushButton"]("Refresh")
        self.recordings_list = qt["QListWidget"]()

        sidebar_layout.addWidget(self.status_label)
        sidebar_layout.addWidget(self.start_button)
        sidebar_layout.addWidget(self.stop_button)
        sidebar_layout.addWidget(self.refresh_button)
        sidebar_layout.addWidget(qt["QLabel"]("Recent recordings"))
        sidebar_layout.addWidget(self.recordings_list)

        main_area = qt["QWidget"]()
        main_layout = qt["QVBoxLayout"](main_area)
        self.review_title = qt["QLabel"]("Select a recording")
        self.frame_preview = qt["QLabel"]("No frame preview")
        self.events_text = qt["QTextEdit"]()
        self.exclude_first_frame_button = qt["QPushButton"]("Exclude first screenshot")
        self.mark_sensitive_button = qt["QPushButton"]("Mark first screenshot sensitive")
        self.compile_button = qt["QPushButton"]("Send to Agent SDK")

        self.frame_preview.setMinimumHeight(260)
        self.frame_preview.setAlignment(_qt_enum(qt["Qt"], "AlignCenter", "AlignmentFlag"))
        self.events_text.setReadOnly(True)
        self.exclude_first_frame_button.setEnabled(False)
        self.mark_sensitive_button.setEnabled(False)

        main_layout.addWidget(self.review_title)
        main_layout.addWidget(self.frame_preview)
        main_layout.addWidget(self.events_text)
        main_layout.addWidget(self.exclude_first_frame_button)
        main_layout.addWidget(self.mark_sensitive_button)
        main_layout.addWidget(self.compile_button)

        splitter.addWidget(sidebar)
        splitter.addWidget(main_area)
        splitter.setSizes([280, 760])
        self.window.setCentralWidget(central)

        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.refresh_button.clicked.connect(self.refresh)
        self.recordings_list.currentRowChanged.connect(self.select_recording)
        self.exclude_first_frame_button.clicked.connect(self.exclude_first_frame)
        self.mark_sensitive_button.clicked.connect(self.mark_first_frame_sensitive)
        self.compile_button.clicked.connect(self.compile_selected)

    def refresh(self) -> None:
        self.refresh_status()
        self.compile_button.setEnabled(False)
        self.exclude_first_frame_button.setEnabled(False)
        self.mark_sensitive_button.setEnabled(False)
        self.selected_recording = None
        self.review = None

        self.refresh_recordings()

    def refresh_recordings(self) -> None:
        self.recordings = self.services.recent_recordings()
        self.recordings_list.blockSignals(True)
        self.recordings_list.clear()
        for recording in self.recordings:
            item = self.qt["QListWidgetItem"](
                f"{recording.name} ({recording.frame_count} frames)"
            )
            item.setToolTip(str(recording.path))
            self.recordings_list.addItem(item)
        self.recordings_list.blockSignals(False)

    def refresh_status(self) -> None:
        was_recording_active = (
            self.current_status is not None
            and self.current_status.recording_active
        )
        status = self.services.status()
        self.current_status = status
        self.status_label.setText(f"{status.state_label}: {status.setup_status}")
        self.start_button.setEnabled(status.can_record and not status.recording_active)
        self.stop_button.setEnabled(status.recording_active)
        if self.selected_recording is not None:
            self.compile_button.setEnabled(self._can_compile_selected())
        if was_recording_active and not status.recording_active:
            self.refresh_recordings()

    def start_recording(self) -> None:
        started = self.services.start_recording()
        if started:
            self.window.statusBar().showMessage("Recording started")
        else:
            self.window.statusBar().showMessage("Recording is already running")
        self.refresh()

    def stop_recording(self) -> None:
        stopped = self.services.stop_recording()
        if stopped:
            self.window.statusBar().showMessage("Recording stop requested")
        else:
            self.window.statusBar().showMessage("No active recording to stop")
        self.refresh()

    def select_recording(self, index: int) -> None:
        if index < 0 or index >= len(self.recordings):
            self._clear_selection("No frame preview")
            return

        recording = self.recordings[index]
        try:
            review = load_recording_review(recording.path)
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._clear_selection("Review unavailable")
            self.window.statusBar().showMessage(f"Could not load recording: {exc}")
            return
        self.selected_recording = recording
        self.review = review
        self.review_title.setText(recording.name)
        self.events_text.setPlainText(
            "\n".join(
                json.dumps(event.data, sort_keys=True)
                for event in review.events
            )
        )
        self._show_first_frame(review)
        self.compile_button.setEnabled(self._can_compile_selected())
        has_frames = bool(review.frames)
        self.exclude_first_frame_button.setEnabled(has_frames)
        self.mark_sensitive_button.setEnabled(has_frames)

    def compile_selected(self) -> None:
        if self.selected_recording is None:
            return
        if not self._can_compile_selected():
            self.window.statusBar().showMessage("Compile is not ready. Check setup and recording state.")
            return
        self.services.compile_recording(self.selected_recording)
        self.window.statusBar().showMessage("Sent recording to Agent SDK")

    def _selected_review(self):
        if self.selected_recording is None:
            return None
        try:
            return load_recording_review(self.selected_recording.path)
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._clear_selection("Review unavailable")
            self.window.statusBar().showMessage(f"Could not load recording: {exc}")
            return None

    def exclude_first_frame(self) -> None:
        review = self._selected_review()
        if review is None or not review.frames:
            return
        review.frames[0].included = False
        review.save()
        self.window.statusBar().showMessage("First screenshot excluded from compile.")
        self.select_recording(self.recordings_list.currentRow())

    def mark_first_frame_sensitive(self) -> None:
        review = self._selected_review()
        if review is None or not review.frames:
            return
        review.frames[0].sensitive = True
        review.frames[0].included = False
        review.save()
        self.window.statusBar().showMessage("First screenshot marked sensitive and excluded.")
        self.select_recording(self.recordings_list.currentRow())

    def _can_compile_selected(self) -> bool:
        return (
            self.current_status is not None
            and self.current_status.can_compile
            and not self.current_status.recording_active
        )

    def _clear_selection(self, frame_message: str) -> None:
        self.selected_recording = None
        self.review = None
        self.review_title.setText("Select a recording")
        self.frame_preview.clear()
        self.frame_preview.setText(frame_message)
        self.events_text.setPlainText("")
        self.compile_button.setEnabled(False)
        self.exclude_first_frame_button.setEnabled(False)
        self.mark_sensitive_button.setEnabled(False)

    def _show_first_frame(self, review) -> None:
        if not review.frames:
            self.frame_preview.clear()
            self.frame_preview.setText("No frame preview")
            return

        frame = review.frames[0]
        if frame.sensitive:
            self.frame_preview.clear()
            self.frame_preview.setText("First screenshot marked sensitive")
            return

        pixmap = self.qt["QPixmap"](str(frame.path))
        if pixmap.isNull():
            self.frame_preview.clear()
            self.frame_preview.setText("Frame preview unavailable")
            return

        self.frame_preview.setText("")
        self.frame_preview.setPixmap(
            pixmap.scaled(
                520,
                320,
                _qt_enum(self.qt["Qt"], "KeepAspectRatio", "AspectRatioMode"),
            )
        )
