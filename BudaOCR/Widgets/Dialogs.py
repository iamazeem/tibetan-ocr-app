import os
import uuid
from uuid import UUID
from typing import Dict, List, Tuple
from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QLabel, QVBoxLayout, QHBoxLayout, \
    QProgressDialog, QPushButton, QListWidget, QListView, QListWidgetItem, QWidget, QTabWidget, QFormLayout, \
    QRadioButton, QCheckBox, QProgressBar, QButtonGroup, QLineEdit

from BudaOCR.Data import BudaOCRData, OCResult, LineDataResult, OCRModel, Theme, AppSettings, OCRSettings, \
    ExportFormat, Language, Encoding
from BudaOCR.Inference import OCRPipeline
from BudaOCR.Runner import OCRBatchRunner
from BudaOCR.Utils import import_local_models


"""
Boiler plate to construct the Button groups based on the available settings
"""


# Languages
def build_languages(active_language: Language) -> Tuple[QButtonGroup, List[QRadioButton]]:
    buttons = []
    button_group = QButtonGroup()
    button_group.setExclusive(True)

    for lang in Language:
        button = QRadioButton(lang.name)
        buttons.append(button)

        if lang == active_language:
            button.setChecked(True)

        button_group.addButton(button)
        button_group.setId(button, lang.value)

    return button_group, buttons


# Export Formats
def build_exporter_settings(active_exporter: ExportFormat) -> Tuple[QButtonGroup, List[QRadioButton]]:
    exporter_buttons = []
    exporters_group = QButtonGroup()
    exporters_group.setExclusive(True)

    for exporter in ExportFormat:
        button = QRadioButton(exporter.name)
        exporter_buttons.append(button)

        if exporter == active_exporter:
            button.setChecked(True)

        exporters_group.addButton(button)
        exporters_group.setId(button, exporter.value)

    return exporters_group, exporter_buttons


# Encodigns
def build_encodings(active_encoding: Encoding) -> Tuple[QButtonGroup, List[QRadioButton]]:
    encoding_buttons = []
    encodings_group = QButtonGroup()
    encodings_group.setExclusive(True)

    for encoding in Encoding:
        button = QRadioButton(encoding.name)
        encoding_buttons.append(button)

        if encoding == active_encoding:
            button.setChecked(True)

        encodings_group.addButton(button)
        encodings_group.setId(button, encoding.value)

    return encodings_group, encoding_buttons


# Dewarping
def build_binary_selection(current_setting: bool) -> Tuple[QButtonGroup, List[QRadioButton]]:
    buttons = []
    button_group = QButtonGroup()
    button_group.setExclusive(True)

    yes_btn = QRadioButton("yes")
    no_btn = QRadioButton("no")

    if current_setting:
        yes_btn.setChecked(True)
    else:
        no_btn.setChecked(True)

    button_group.addButton(yes_btn)
    button_group.addButton(no_btn)

    button_group.setId(no_btn, 0)
    button_group.setId(yes_btn, 1)

    buttons.append(yes_btn)
    buttons.append(no_btn)

    return button_group, buttons


class ImportFilesDialog(QFileDialog):
    def __init__(self, parent=None):
        super(ImportFilesDialog, self).__init__(parent)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)
        self.setNameFilter("Images (*.png *.jpg *.tif *.tiff)")
        self.setViewMode(QFileDialog.ViewMode.List)


class ImportDirDialog(QFileDialog):
    def __init__(self, parent=None):
        super(ImportDirDialog, self).__init__(parent)
        self.setFileMode(QFileDialog.FileMode.Directory)


class ConfirmationDialog(QMessageBox):
    def __init__(self, title: str, message: str, show_cancel: bool = True):
        super().__init__()
        self.setObjectName("ConfirmWindow")
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setMinimumHeight(440)
        self.setIcon(QMessageBox.Icon.Information)
        self.setText(message)

        self.ok_btn = QPushButton("Ok")
        self.cancel_btn = QPushButton("Cancel")

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.ok_btn.setStyleSheet("""
                color: #000000;
                font: bold 12px;
                width: 240px;
                height: 32px;
                background-color: #ffad00;
                border: 2px solid #ffad00;
                border-radius: 4px;

                QPushButton::hover { 
                    color: #ff0000;
                }

            """)

        self.cancel_btn.setStyleSheet("""
                color: #000000;
                font: bold 12px; 
                width: 240px;
                height: 32px;
                background-color: #ffad00;
                border: 2px solid #ffad00;
                border-radius: 4px;

                QPushButton::hover {
                    color: #ff0000;
                }
            """)

        if show_cancel:
            self.addButton(self.ok_btn, QMessageBox.ButtonRole.YesRole)
            self.addButton(self.cancel_btn, QMessageBox.ButtonRole.NoRole)
        else:
            self.addButton(self.ok_btn, QMessageBox.ButtonRole.YesRole)

        self.setStyleSheet("""
                background-color: #292951;
                color: #ffffff;
        """)


class NotificationDialog(QMessageBox):
    def __init__(self, title: str, message: str):
        super().__init__()
        self.setObjectName("NotificationWindow")
        self.setWindowTitle(title)
        self.setMinimumWidth(600)
        self.setMinimumHeight(440)
        self.setIcon(QMessageBox.Icon.Information)
        self.setStandardButtons(QMessageBox.Ok)
        self.setText(message)

        self.setStyleSheet("""
                    color: #ffffff;
                    QPushButton {
                        width: 200px;
                        padding: 5px;
                        background-color: #4d4d4d;
                    }
                """)


class ModelListWidget(QWidget):
    def __init__(self, guid: UUID, title: str, encoder: str, architecture: str):
        super().__init__()
        self.guid = guid
        self.title = str(title)
        self.encoder = str(encoder)
        self.architecture = str(architecture)

        self.title_label = QLabel(self.title)
        self.encoder_label = QLabel(self.encoder)
        self.architecture_label = QLabel(self.architecture)
        self.download_btn = QPushButton('Download')
        self.delete_btn = QPushButton('Delete')

        # build layout
        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(self.title_label)
        self.h_layout.addWidget(self.encoder_label)
        self.h_layout.addWidget(self.architecture_label)
        self.h_layout.addWidget(self.download_btn)
        self.h_layout.addWidget(self.delete_btn)
        self.setLayout(self.h_layout)

        self.setStyleSheet("""
            color: #ffffff;
            width: 80%;
        """)

class ModelEntryWidget(QWidget):
    def __init__(self, guid: UUID, title: str, encoder: str, architecture: str):
        super().__init__()
        self.guid = guid
        self.title = str(title)
        self.encoder = str(encoder)
        self.architecture = str(architecture)

        self.title_label = QLabel(self.title)
        self.encoder_label = QLabel(self.encoder)
        self.architecture_label = QLabel(self.architecture)
        # build layout
        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(self.title_label)
        self.h_layout.addWidget(self.encoder_label)
        self.h_layout.addWidget(self.architecture_label)
        self.setLayout(self.h_layout)

        self.setStyleSheet("""
            color: #ffffff;
            width: 80%;
        """)


class ModelList(QListWidget):
    sign_on_selected_item = Signal(UUID)

    def __init__(self, parent=None):
        super(ModelList, self).__init__(parent)
        self.parent = parent
        self.setObjectName("ModelListItem")
        self.setFlow(QListView.Flow.TopToBottom)
        self.setMouseTracking(True)
        self.itemClicked.connect(self.on_item_clicked)

        self.setStyleSheet(
            """
            background-color: #172832;
            border-radius: 4px;

            """)

    def on_item_clicked(self, item: QListWidgetItem):
        _list_item_widget = self.itemWidget(
            item
        )  # returns an instance of CanvasHierarchyEntry

        if isinstance(_list_item_widget, ModelListWidget):
            print(f"Clicked on Model: {_list_item_widget.title}")
            self.sign_on_selected_item.emit(_list_item_widget.guid)


class SettingsDialog(QDialog):
    def __init__(self, app_settings: AppSettings, ocr_settings: OCRSettings, ocr_models: List[OCRModel]):
        super().__init__()
        self.app_settings = app_settings
        self.ocr_settings = ocr_settings
        self.ocr_models = ocr_models
        self.model_list = ModelList(self)

        self.selected_theme = Theme.Dark
        self.selected_exporters = []

        # Settings
        # Theme
        self.dark_theme_btn = QRadioButton("Dark")
        self.light_theme_btn = QRadioButton("Light")

        self.theme_group = QButtonGroup()
        self.theme_group.setExclusive(True)
        self.theme_group.addButton(self.dark_theme_btn)
        self.theme_group.addButton(self.light_theme_btn)
        self.theme_group.setId(self.dark_theme_btn, Theme.Dark.value)
        self.theme_group.setId(self.light_theme_btn, Theme.Light.value)

        if self.app_settings.theme == Theme.Dark:
            self.dark_theme_btn.setChecked(True)
            self.light_theme_btn.setChecked(False)
        else:
            self.dark_theme_btn.setChecked(False)
            self.light_theme_btn.setChecked(True)

        self.import_models_btn = QPushButton("Import Models")
        self.import_models_btn.clicked.connect(self.handle_model_import)

        self.exporter_group, self.exporter_buttons = build_exporter_settings(self.ocr_settings.exporter)
        self.encodings_group, self.encoding_buttons = build_encodings(self.app_settings.encoding)
        self.language_group, self.language_buttons = build_languages(self.app_settings.language)
        self.dewarp_group, self.dewarp_buttons = build_binary_selection(self.ocr_settings.dewarping)

        self.setWindowTitle("BudaOCR Settings")
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # define layout
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setContentsMargins(0, 0, 0, 0)

        self.settings_tabs.setStyleSheet(
            """
                QTabWidget::pane {
                    border: None;
                    padding-top: 20px;
                }
        """)

        # General Settings Tab
        self.general_settings_tab = QWidget()
        form_layout = QFormLayout()
        form_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ui_theme = QHBoxLayout()
        ui_theme.addWidget(self.dark_theme_btn)
        ui_theme.addWidget(self.light_theme_btn)

        language_layout = QHBoxLayout()

        for btn in self.language_buttons:
            language_layout.addWidget(btn)

        form_layout.addRow(QLabel("UI Theme"), ui_theme)
        form_layout.addRow(QLabel("Language"), language_layout)
        self.general_settings_tab.setLayout(form_layout)

        # OCR Models Tab
        self.ocr_models_tab = QWidget()
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Available OCR Models"))
        h_layout.addWidget(self.import_models_btn)

        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.model_list)
        self.ocr_models_tab.setLayout(v_layout)

        # OCR Settings Tab
        self.ocr_settings_tab = QWidget()
        form_layout = QFormLayout()
        form_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        encoding_layout = QHBoxLayout()

        for encoding in self.encoding_buttons:
            encoding_layout.addWidget(encoding)

        dewarping_layout = QHBoxLayout()

        for btn in self.dewarp_buttons:
            dewarping_layout.addWidget(btn)

        export_layout = QHBoxLayout()
        for btn in self.exporter_buttons:
            export_layout.addWidget(btn)

        form_layout.addRow(QLabel("Encoding"), encoding_layout)
        form_layout.addRow(QLabel("Dewarping"), dewarping_layout)
        form_layout.addRow(QLabel("Export Formats"), export_layout)
        self.ocr_settings_tab.setLayout(form_layout)


        # build entire Layout
        self.settings_tabs.addTab(self.general_settings_tab, "General")
        self.settings_tabs.addTab(self.ocr_models_tab, "OCR Models")
        self.settings_tabs.addTab(self.ocr_settings_tab, "OCR Settings")

        self.main_v_layout = QVBoxLayout()
        self.main_v_layout.addWidget(self.settings_tabs)

        self.button_h_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Ok")
        self.cancel_btn = QPushButton("Cancel")

        self.button_h_layout.addWidget(self.ok_btn)
        self.button_h_layout.addWidget(self.cancel_btn)
        self.main_v_layout.addLayout(self.button_h_layout)
        self.setLayout(self.main_v_layout)

        # bind signals
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.import_models_btn.setStyleSheet("""
            QPushButton {
                    color: #A40021;
                    background-color: #fce08d;
                    border-radius: 4px;
                    height: 18;
                }
                
            QPushButton::hover {
                    color: #ffad00;
                }
                
        """)
        self.ok_btn.setStyleSheet(
            """
                QPushButton {
                    margin-top: 15px;
                    background-color: #A40021;
                    border-radius: 4px;
                    height: 24;
                }

                QPushButton::hover {
                    color: #ffad00;
                }
            """)

        self.cancel_btn.setStyleSheet(
            """
                QPushButton {
                    margin-top: 15px;
                    background-color: #A40021;
                    border-radius: 4px;
                    height: 24;
                }

                QPushButton::hover {
                    color: #ffad00;
                }
            """)

        self.setStyleSheet(
            """
            background-color: #1d1c1c;
            color: #ffffff;
        
            QLabel {
                color: #000000;
            }
            QDialogButtonBox::Ok {
                height: 32px;
                width: 64px;
            }
            QDialogButtonBox::Cancel {
                height: 32px;
                width: 64px;
            }
            """)

        self.build_model_overview()

    def handle_accept(self):
        self.accept()

    def handle_reject(self):
        self.reject()

    def build_model_overview(self):
        self.model_list.clear()

        for model in self.ocr_models:
            model_item = QListWidgetItem(self.model_list)
            #model_widget = ModelListWidget(guid=uuid.uuid1(),title=model.name)
            model_widget = ModelEntryWidget(
                guid=model.guid,
                title=model.name,
                encoder=model.config.encoder.name,
                architecture=model.config.architecture.name
            )

            model_item.setSizeHint(model_widget.sizeHint())
            self.model_list.addItem(model_item)
            self.model_list.setItemWidget(model_item, model_widget)

    def clear_models(self):
        self.model_list.clear()

    def handle_model_import(self):
        _dialog = ImportDirDialog()
        selected_dir = _dialog.exec()

        if selected_dir == 1:
            _selected_dir = _dialog.selectedFiles()[0]

            if os.path.isdir(_selected_dir):
                try:
                    imported_models = import_local_models(_selected_dir)
                    confirm_dialog = ConfirmationDialog(
                        title="Confirm Model Import",
                        message="Do you want to import the new models and replace the old ones?"
                    )
                    confirm_dialog.exec()
                    result = confirm_dialog.result()

                    if result == 2:
                        print(f"Result: {result}")
                        self.ocr_models = imported_models
                        self.build_model_overview()
                    else:
                        print("Skipping import of new models")

                except BaseException as e:
                    error_dialog = NotificationDialog("Model import failed", f"Importing Models Failed: {e}")
                    error_dialog.exec()

    def exec(self):
        super().exec()

        # fetch settings
        theme_id = self.theme_group.checkedId()
        self.app_settings.theme = Theme(theme_id)

        language_id = self.language_group.checkedId()
        self.app_settings.language = Language(language_id)

        encoding_id = self.encodings_group.checkedId()
        self.app_settings.encoding = Encoding(encoding_id)

        exporters_id = self.exporter_group.checkedId()
        self.ocr_settings.exporter = ExportFormat(exporters_id)

        dewarp_id = self.dewarp_group.checkedId()
        do_dewarp = bool(dewarp_id)
        self.ocr_settings.dewarping = do_dewarp

        return self.app_settings, self.ocr_settings

class BatchOCRDialog(QDialog):
    def __init__(self, data: List[BudaOCRData], ocr_pipeline: OCRPipeline, ocr_models: List[OCRModel], ocr_settings: OCRSettings, threadpool: QThreadPool):
        super().__init__()
        self.data = data
        self.pipeline = ocr_pipeline
        self.ocr_models = ocr_models
        self.ocr_settings = ocr_settings
        self.threadpool = threadpool
        self.runner = None

        self.setMinimumWidth(600)
        self.setMaximumWidth(1200)
        self.setFixedHeight(280)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(self.data))

        self.start_process_btn = QPushButton("Start")
        self.cancel_process_btn = QPushButton("Cancel")

        # settings elements
        # Exports
        self.exporter_group, self.exporter_buttons = build_exporter_settings(self.ocr_settings.exporter)
        self.encodings_group, self.encoding_buttons = build_encodings(self.ocr_settings.output_encoding)
        self.dewarp_group, self.dewarp_buttons = build_binary_selection(self.ocr_settings.dewarping)

        # build layout

        self.progress_layout = QHBoxLayout()
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.start_process_btn)
        self.progress_layout.addWidget(self.cancel_process_btn)

        self.button_h_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Ok")
        self.ok_btn.setObjectName("DialogButton")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("DialogButton")

        self.button_h_layout.addWidget(self.ok_btn)
        self.button_h_layout.addWidget(self.cancel_btn)

        self.v_layout = QVBoxLayout()
        self.label = QLabel("Batch Processing")

        self.export_dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_select = QPushButton("select")
        self.export_dir_layout.addWidget(self.dir_edit)
        self.export_dir_layout.addWidget(self.dir_select)

        self.form_layout = QFormLayout()
        self.form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        encoding_layout = QHBoxLayout()
        for btn in self.encoding_buttons:
            encoding_layout.addWidget(btn)

        dewarping_layout = QHBoxLayout()
        for btn in self.dewarp_buttons:
            dewarping_layout.addWidget(btn)

        export_layout = QHBoxLayout()
        for btn in self.exporter_buttons:
            export_layout.addWidget(btn)

        self.form_layout.addRow(QLabel("Output Encoding"), encoding_layout)
        self.form_layout.addRow(QLabel("Dewarping"), dewarping_layout)
        self.form_layout.addRow(QLabel("Export Formats"), export_layout)

        self.v_layout.addWidget(self.label)
        self.v_layout.addLayout(self.export_dir_layout)
        self.v_layout.addLayout(self.form_layout)
        self.v_layout.addLayout(self.progress_layout)
        self.v_layout.addLayout(self.button_h_layout)

        self.setLayout(self.v_layout)

        # bind signals
        self.dir_select.clicked.connect(self.select_export_dir)
        self.start_process_btn.clicked.connect(self.start_process)
        self.cancel_process_btn.clicked.connect(self.cancel_process)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def select_export_dir(self):
        dialog = ImportDirDialog()
        selected_dir = dialog.exec()

        if selected_dir == 1:
            _selected_dir = dialog.selectedFiles()[0]

            if os.path.isdir(_selected_dir):
                self.dir_edit.setText(_selected_dir)
        else:
            note_dialog = NotificationDialog("Invalid Directory", "The selected directory is not valid.")
            note_dialog.exec()

    def start_process(self):
        encoding_id = self.encodings_group.checkedId()
        encoding = Encoding(encoding_id)

        self.runner = OCRBatchRunner(self.data, self.pipeline, output_encoding=encoding)
        self.runner.signals.sample.connect(self.handle_update_progress)
        self.runner.signals.batch_ocr_result.connect(self.handle_ocr_result)
        self.runner.signals.finished.connect(self.finish)
        self.threadpool.start(self.runner)

    def handle_update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def handle_ocr_result(self, result: Dict[UUID, OCResult]):
        print(f"Got OCR Result: {result}")

    def finish(self):
        print(f"Thread Completed")
        self.runner = None

    def cancel_process(self):
        self.runner.stop = True


class OCRBatchProgress(QProgressDialog):
    sign_line_result = Signal(LineDataResult)
    sign_ocr_result = Signal(OCResult)

    def __init__(self, data: list[BudaOCRData], pool: QThreadPool):
        super(OCRBatchProgress, self).__init__()
        self.setObjectName("OCRDialog")
        self.setMinimumWidth(500)
        self.setWindowTitle("OCR Progress")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimum(0)
        self.setMaximum(0)

        self.data = data
        self.pool = pool

        self.start_btn = QPushButton("Start")
        self.cancel_btn = QPushButton("Cancel")

        self.cancel_btn.setStyleSheet("""

                QPushButton {
                    margin-top: 15px;
                    background-color: #ff0000;
                }

                QPushButton::hover {
                    color: #ffad00;
                }

            """)

        self.setCancelButton(self.cancel_btn)
        self.setStyleSheet("""

            background-color: #08081f;

            QProgressBar {
                background-color: #24272c;
                border-radius: 5px;
                border-width: 2px;
            }

            QProgressBar::chunk
            {
                background-color: #003d66;
                border-radius: 5px;
                margin: 3px 3px 3px 3px;
            }
        """)

        self.show()

    def exec(self):
        """
        runner = OCRunner(self.data, self.line_detection, self.layout_detection, self.line_mode)
        runner.signals.sample.connect(self.handle_update_progress)
        runner.signals.error.connect(self.close)
        runner.signals.line_result.connect(self.handle_line_result)
        runner.signals.ocr_result.connect(self.handle_ocr_result)
        runner.signals.finished.connect(self.thread_complete)
        self.pool.start(runner)
        """

    def handle_update_progress(self, value: int):
        print(f"Processing sample: {value}")

    def handle_error(self, error: str):
        print(f"Encountered Error: {error}")

    def handle_ocr_result(self, result: OCResult):
        #self.sign_sam_result.emit(result)
        pass

    def handle_line_result(self, result: LineDataResult):
        #self.sign_batch_result.emit(result)
        pass

    def thread_complete(self):
        self.close()