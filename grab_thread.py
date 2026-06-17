import numpy as np
import pyvirtualcam
from pypylon import pylon
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import settings


class GrabThread(QObject):

    avg_fps = pyqtSignal(float)
    frame_grabbed = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    vga_resolution = (854, 480)

    def __init__(self):
        super().__init__()
        self.running = True
        self.camera = None
        self.virt_cam = None
        self.preview_enabled = False

    def stop(self):
        self.running = False

    def set_camera(self, camera):
        self.camera = camera
        self.camera.PixelFormat = "Mono8"
        self.input_res = settings.get_setting(
            "input_resolution", [self.camera.Width.Value, self.camera.Height.Value])
        self.output_res = settings.get_setting(
            "output_resolution", [self.camera.Width.Value, self.camera.Height.Value])
        self.fps = settings.get_setting("fps", 30)
        self.camera.UserSetSelector.Value = "UserSet1"
        self.camera.UserSetLoad.Execute()
        self.virt_cam = pyvirtualcam.Camera(width=self.output_res[0],
                                            height=self.output_res[1],
                                            fps=self.fps,
                                            backend=None,
                                            print_fps=False, fmt=pyvirtualcam.PixelFormat.GRAY)
        self.frame = np.full(
            (self.camera.Height.Value, self.camera.Width.Value, 1), 255, np.uint8)

    def enable_preview(self):
        self.preview_enabled = True

    def disable_preview(self):
        self.preview_enabled = False

    def run(self):
        self.camera.MaxNumBuffer = 100
        self.camera.StartGrabbingMax(
            1_000_000_000, pylon.GrabStrategy_LatestImages)
        i = 0
        while self.running:

            try:
                grabResult = self.camera.RetrieveResult(
                    5000, pylon.TimeoutHandling_Return)
                # Image grabbed successfully?
                if grabResult.GrabSucceeded():
                    self.frame = grabResult.Array
                grabResult.Release()
            except: #genicam.GenericException as e:
                self.running = False

            if self.output_res != self.input_res:
                self.virt_cam.send(cv2.resize(
                    self.frame, tuple(self.output_res)))
            else:
                self.virt_cam.send(self.frame)

            self.frame_grabbed.emit(self.frame)

            if i % 10 == 0:
                self.avg_fps.emit(self.virt_cam._fps_counter.avg_fps)

            self.virt_cam.sleep_until_next_frame()
            i += 1

        self.virt_cam.close()
        self.camera.Close()
        self.virt_cam = None
        self.camera = None
        self.running = False
        self.preview_enabled = False
        self.finished.emit()
        self.avg_fps.emit(0)


def set_int_value(feature, value):
    val_0_min = value - feature.Min
    val_corr_inc = (val_0_min // feature.Inc) * feature.Inc

    val = min(max(val_corr_inc + feature.Min, feature.Min), feature.Max)

    feature.Value = int(val)