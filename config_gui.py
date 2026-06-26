from pypylon import pylon
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ConfigGui(QWidget):

    def __init__(self, grab_thread, preview_thread):
        super().__init__()

        vbox = QVBoxLayout()
        self.camera = None

        self.camera_list = QComboBox()
        self.discover_button = QPushButton("Discover")
        self.discover_button.clicked.connect(self.discover_cameras)
        self.connect_button = QPushButton("Open")
        self.connect_button.clicked.connect(self.connect_camera)
        
        discover_box = QHBoxLayout()
        discover_box.addWidget(self.camera_list)
        discover_box.addWidget(self.discover_button)
        discover_box.addWidget(self.connect_button)

        vbox.addLayout(discover_box)

        self.camera_feature_box = QVBoxLayout()
        vbox.addLayout(self.camera_feature_box)
        vbox.addStretch()

        self.footer_box = QHBoxLayout()
        vbox.addLayout(self.footer_box)
        self.avg_fps_label = QLabel("FPS:   0.00 | Latency: --- ms")
        self.footer_box.addWidget(self.avg_fps_label)
        self.footer_box.addStretch()
        self.latency_label = QLabel("Latency: --- ms")
        self.footer_box.addWidget(self.latency_label)
        self.footer_box.addStretch()
        self.preview_enabled = False
        self.preview_toggle = QPushButton("Show Preview")
        self.preview_toggle.setDisabled(True)
        self.preview_toggle.clicked.connect(self.on_preview_toggle)
        self.footer_box.addWidget(self.preview_toggle)
        self.setLayout(vbox)
        self.setGeometry(100, 100, 420, 320)
        self.setWindowTitle("Pylon Webcam")

        self.setup_minimize_to_tray()

        self.grab_thread = grab_thread
        self.thread = QThread()
        self.grab_thread.moveToThread(self.thread)
        self.thread.started.connect(self.grab_thread.run)
        self.grab_thread.finished.connect(self.grab_thread_finished)
        self.grab_thread.avg_fps.connect(self.update_avg_fps)
        self.grab_thread.latency_ms.connect(self.update_latency)

        self.preview_thread = preview_thread
        self.prev_thread = QThread()
        self.preview_thread.moveToThread(self.prev_thread)
        self.preview_thread.preview_toggle.connect(self.on_preview_toggle)
        self.prev_thread.started.connect(self.preview_thread.run)
        self.prev_thread.start()

        self.discover_cameras()
        #self.connect_camera()

        self.show()

    def setup_minimize_to_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('pylon_webcam_icon_64.png'))

        show_action = QAction("Show", self)
        quit_action = QAction("Exit")
        hide_action = QAction("Hide")
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(qApp.quit)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_preview_toggle(self):
        if self.preview_enabled:
            self.preview_toggle.setText("Show Preview")
            self.preview_thread.disable_preview()
        else:
            self.preview_toggle.setText("Disable Preview")
            self.preview_thread.enable_preview()

        self.preview_enabled = not self.preview_enabled

    def on_tray_icon_activated(self, event):
        if event == QSystemTrayIcon.DoubleClick:
            self.show()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                if self.preview_enabled:
                    self.preview_enabled = False
                    self.preview_toggle.setText("Show Preview")
                    self.preview_thread.disable_preview()
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "Pylon Webcam",
                    "Application was minimized to Tray",
                    1000
                )

    def show(self):
        super().show()
        self.setWindowState(Qt.WindowNoState)

    def grab_thread_finished(self):
        self.connect_button.setDisabled(False)
        clearLayout(self.camera_feature_box)
        self.discover_cameras()


    def update_avg_fps(self, value):
        self.avg_fps_label.setText(f"FPS:   {value:.2f}")

    def update_latency(self, latency_ms):
        # Update latency with 2 decimal places and pad to align with FPS display
        latency_str = f"{latency_ms:.2f}"
        self.latency_label.setText(f"Latency: {latency_str} ms")

    def discover_cameras(self):
        self.full_name_list = []
        self.camera_list.clear()
        devices = pylon.TlFactory.GetInstance().EnumerateDevices()
        self.camera_list.setDisabled(len(devices) == 0)
        self.connect_button.setDisabled(len(devices) == 0)
        for cam in devices:
            self.camera_list.addItem(cam.GetFriendlyName())
            self.full_name_list.append(cam.GetFullName())

    def connect_camera(self):
        if self.camera is None:
            try:
                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(
                    self.full_name_list[self.camera_list.currentIndex()]))
                self.camera.Open()
            except:
                QMessageBox.critical(
                    self, "Error", f"Selected Camera\n{self.camera_list.currentText()}\ncould not be opened")
                self.camera = None
                return

            self.grab_thread.set_camera(self.camera)
            self.preview_toggle.setDisabled(False)
            self.thread.start()
            self.connect_button.setText("Close")
            self.setup_camera_features()

        else:
            self.grab_thread.stop()
            self.connect_button.setDisabled(True)
            self.preview_toggle.setDisabled(True)
            if self.preview_enabled:
                self.preview_enabled = False
                self.preview_toggle.setText("Show Preview")
                self.preview_thread.disable_preview()
            self.connect_button.setText("Open")
            self.camera = None
            clearLayout(self.camera_feature_box)

            self.thread.exit()
            self.thread.wait()

    def setup_camera_features(self):
        clearLayout(self.camera_feature_box)

        features = [
            ("Gamma", SliderFeature, "Gamma"),
            ("BslContrast", SliderFeature, "Contrast"),
            ("BslBrightness", SliderFeature, "Brightness"),
            ]

        for attr_name, feature_class, label in features:
            try:
                if hasattr(self.camera, attr_name):
                    feature = feature_class(getattr(self.camera, attr_name), label)
                    self.camera_feature_box.addLayout(feature.get_layout())
            except Exception as e:
                print(f"Skipped {attr_name}: {e}")


def clearLayout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                clearLayout(item.layout())


class SliderFeature:

    def __init__(self, feature, name):
        self.feature = feature
        if self.feature.HasInc():
            self.SLIDER_INC = self.feature.Inc
        else:
            self.SLIDER_INC = 0.01

        self.SLIDER_MAX = self.feature.Max
        self.SLIDER_MIN = self.feature.Min

        self.label = QLabel(name)

        self.slider = DoubleSlider(self.SLIDER_INC, Qt.Horizontal)
        self.slider.setRange(self.SLIDER_MIN, self.SLIDER_MAX)
        self.slider.setValue(self.feature.Value)
        self.slider.setFixedWidth(200)
        self.slider.doubleValueChanged.connect(self.value_changed_slider)

        self.spin_box = QDoubleSpinBox()
        self.spin_box.setRange(self.SLIDER_MIN, self.SLIDER_MAX)
        self.spin_box.setSingleStep(self.SLIDER_INC)
        self.spin_box.setValue(self.feature.Value)
        self.spin_box.setFixedWidth(70)
        self.spin_box.valueChanged.connect(self.value_changed_spin)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addStretch()
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.spin_box)

    def get_layout(self):
        return self.layout

    def value_changed_spin(self, value):
        self.feature.Value = value
        if value != self.slider.value():
            self.slider.setValue(value)

    def value_changed_slider(self, value):
        self.feature.Value = value
        if value != self.spin_box.value():
            self.spin_box.setValue(value)


class EnumFeature:

    def __init__(self, feature, name):
        self.feature = feature
        self.label = QLabel(name)
        self.combobox = QComboBox()
        self.enumText = self.feature.GetSymbolics()
        self.combobox.addItems(self.enumText)
        self.combobox.setCurrentText(
            self.feature.GetCurrentEntry().GetSymbolic())
        self.combobox.currentIndexChanged.connect(self.index_changed)

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addStretch()
        self.layout.addWidget(self.combobox)

    def get_layout(self):
        return self.layout

    def index_changed(self, index):
        self.feature.Value = self.combobox.currentText()


class DoubleSlider(QSlider):

    # create our our signal that we can connect to if necessary
    doubleValueChanged = pyqtSignal(float)

    def __init__(self, inc, *args, **kargs):
        super(DoubleSlider, self).__init__(*args, **kargs)
        self._inc = inc

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super(DoubleSlider, self).value()) * self._inc
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super(DoubleSlider, self).value()) * self._inc

    def setMinimum(self, value):
        return super(DoubleSlider, self).setMinimum(value / self._inc)

    def setMaximum(self, value):
        return super(DoubleSlider, self).setMaximum(value / self._inc)

    def setRange(self, min_, max_):
        return super(DoubleSlider, self).setRange(min_ / self._inc, max_ / self._inc)

    def setSingleStep(self, value):
        return super(DoubleSlider, self).setSingleStep(value / self._inc)

    def singleStep(self):
        return float(super(DoubleSlider, self).singleStep()) * self._inc

    def setValue(self, value):
        super(DoubleSlider, self).setValue(int(value / self._inc))