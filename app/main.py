import signal
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from .ui_editor import ProfileEditor
from .ini_utils import resource_path


def run():
    app = QApplication(sys.argv)
    # Organization + application name are required for QSettings to land
    # in the canonical platform location (e.g. ~/Library/Preferences on
    # macOS) — used to persist the user's device-type preference.
    app.setOrganizationName("TeensyRecorders")
    app.setApplicationName("ProfilesEditor")

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    # Wake the Qt loop periodically so Python can handle SIGINT
    sigint_timer = QTimer()
    sigint_timer.start(200)
    sigint_timer.timeout.connect(lambda: None)

    ini_file = resource_path("initial_profile/Profiles.ini")
    logo_file = resource_path("img/logo_PR.png")

    window = ProfileEditor(str(ini_file), logo_path=str(logo_file))
    window.resize(500, 900)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
