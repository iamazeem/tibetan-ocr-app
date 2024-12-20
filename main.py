
"""
- build for windows: nuitka --standalone --windows-console-mode=disable --plugin-enable=pyside6 --windows-icon-from-ico=logo.ico --include-data-dir=./Assets=Assets --include-data-dir=./Models=Models main.py
- debug build for windows: nuitka --standalone --plugin-enable=pyside6 --windows-icon-from-ico=logo.ico --include-data-dir=./Assets=Assets --include-data-dir=./Models=Models main.py
- build for macos: nuitka --standalone --plugin-enable=pyside6 --macos-create-app-bundle --macos-app-icon=logo.icns --include-data-dir=./Assets=Assets --include-data-dir=./Models=Models main.py

Note:
    If you edit the resources.qrc file, make sure to recompile it by using: pyside6-rcc resources.qrc -o resources.py
"""

import os
import sys
from appdirs import user_data_dir
from glob import glob
from PySide6.QtCore import QPoint
from BDRC.MVVM.view import AppView
from BDRC.MVVM.model import OCRDataModel, SettingsModel
from BDRC.MVVM.viewmodel import DataViewModel, SettingsViewModel
from Config import read_settings, LINES_CONFIG
from BDRC.Utils import get_screen_center, set_user_dir, get_platform, create_dir
from PySide6.QtWidgets import QApplication
from BDRC.Styles import DARK

APP_NAME = "OCR"
APP_AUTHOR = "BDRC"

if __name__ == "__main__":
    platform = get_platform()
    user_data_dir = user_data_dir(APP_NAME, APP_AUTHOR)
    set_user_dir(user_data_dir)
    create_dir(user_data_dir)

    app = QApplication()
    app.setStyleSheet(DARK)

    app_settings, ocr_settings = read_settings(user_data_dir)

    data_model = OCRDataModel()
    settings_model = SettingsModel(app_settings, ocr_settings)

    dataview_model = DataViewModel(data_model)
    settingsview_model = SettingsViewModel(settings_model)

    screen_data = get_screen_center(app)

    app_view = AppView(
        dataview_model,
        settingsview_model,
        platform,
        user_data_dir
    )
    app_view.resize(screen_data.start_width, screen_data.start_height)
    app_view.move(QPoint(screen_data.start_x, screen_data.start_y))


    # just delete tmp files on startup
    tmp_img_dir = os.path.join(user_data_dir, "tmp", "images")
    print(f"Tmp image dir: {tmp_img_dir}")

    if os.path.isdir(tmp_img_dir):
        tmp_files = glob(f"{tmp_img_dir}/*")
        print(f"Tmp files: {len(tmp_files)}")
        if len(tmp_files) > 0:
            for file in tmp_files:
                os.remove(file)
    else:
        print("tmp dir not a valid dir")

    sys.exit(app.exec())
