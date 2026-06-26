import numpy as np
import pyvirtualcam
from pypylon import pylon
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cv2
import time
import settings


class GrabThread(QObject):
    avg_fps = pyqtSignal(float)
    frame_grabbed = pyqtSignal(np.ndarray)
    finished = pyqtSignal()
    vga_resolution = (854, 480)
    latency_ms = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.running = True
        self.camera = None
        self.virt_cam = None
        self.preview_enabled = False
        # Latency tracking for diagnostics
        self.last_frame_time = []

    def stop(self):
        self.running = False

    def set_camera(self, camera):
        self.camera = camera
        self.input_res = self.camera.Width.Value, self.camera.Height.Value
        # Read desired output resolution from settings
        desired_output_res = settings.get_setting("output_resolution", None)
        
        # If no specific output resolution is set, try to use a safe default based on camera resolution
        if desired_output_res is None:
            max_obs_width = min(self.input_res[0], 1920)  # OBS Virtual Camera typically handles up to ~1920x1080 for grayscale
            max_obs_height = min(self.input_res[1], 1080)
            desired_output_res = (max_obs_width, max_obs_height)
        
        self.output_res = desired_output_res
        self.fps = settings.get_setting("fps", 30)
        print(f"[DEBUG] Input resolution: {self.input_res}, Output resolution: {self.output_res}, FPS: {self.fps}")
        print(f"[DEBUG] Camera resolution: {self.camera.Width.Value}x{self.camera.Height.Value}, PixelFormat: {self.camera.PixelFormat.Value}")
        self.max_buffer_frames = settings.get_setting("max_buffer_frames", 5)
        self.camera.UserSetSelector.Value = "UserSet1"
        self.camera.UserSetLoad.Execute()
        self.virt_cam = pyvirtualcam.Camera(width=self.output_res[0],
                                            height=self.output_res[1],
                                            fps=self.fps,
                                            backend="obs",
                                            device="OBS Virtual Camera",
                                            print_fps=False, fmt=pyvirtualcam.PixelFormat.GRAY)
        # Store frame as 2D grayscale for pyvirtualcam compatibility
        self.frame = np.full(
            (self.output_res[1], self.output_res[0]), 255, np.uint8)

    def enable_preview(self):
        self.preview_enabled = True

    def disable_preview(self):
        self.preview_enabled = False

    def _fill_buffer(self, num_frames):
        """Pre-fill virtualcam buffer with frames before external apps connect."""
        # Disable pre-fill in settings if needed by setting max_buffer_frames to 0
        if num_frames <= 0:
            print("[DEBUG] Buffer pre-fill disabled via settings")
            return
            
        print(f"[DEBUG] Pre-filling OBS buffer with {num_frames} frames...")
        for j in range(num_frames):
            try:
                grabResult = self.camera.RetrieveResult(200, pylon.TimeoutHandling_Return)
                if grabResult.GrabSucceeded():
                    self.frame = grabResult.Array
                    # Resize frame to match output resolution (critical for high-res cameras!)
                    self.frame = self._resize_frame(self.frame)
                    self.virt_cam.send(self.frame)
                    print(f"[DEBUG] Buffer frame {j+1}/{num_frames} sent")
                grabResult.Release()
            except Exception as e:
                print(f"Buffer fill warning (frame {j+1}): {e}")
                break

    def _resize_frame(self, frame):
        """Resize frame from input resolution to output resolution with aspect handling."""
        in_w, in_h = self.input_res
        out_w, out_h = self.output_res
        
        if in_w == out_w and in_h == out_h:
            return frame
        
        # Read aspect mode setting (default to "letterbox" for proper composition)
        aspect_mode = settings.get_setting("aspect_mode", "letterbox")
        
        # Calculate scale factors relative to input
        scale_x = out_w / in_w
        scale_y = out_h / in_h
        
        if aspect_mode == "letterbox":
            # Letterbox: fit within output bounds while maintaining input aspect ratio
            scale = min(scale_x, scale_y)  # Scale so image fits entirely within output
    
            new_w = int(in_w * scale)
            new_h = int(in_h * scale)
            
            # Resize to scaled dimensions using INTER_LINEAR for better quality at lower resolution
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Calculate padding needed to fill output resolution
            pad_x = (out_w - new_w) // 2
            pad_y = (out_h - new_h) // 2
            
            # Add black borders for letterboxing effect using cv2.BORDER_CONSTANT
            frame = cv2.copyMakeBorder(
                frame,
                top=pad_y, bottom=pad_y,   # vertical padding
                left=pad_x, right=pad_x,   # horizontal padding
                borderType=cv2.BORDER_CONSTANT,
                value=0  # black borders for grayscale
            )
        
        elif aspect_mode == "crop":
            # Crop: maintain input aspect ratio but crop excess to fit output exactly
            scale = min(scale_x, scale_y)
            new_w = int(in_w * scale)
            new_h = int(in_h * scale)
            
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Crop center to match output resolution exactly
            dx1 = (new_w - out_w) // 2
            dy1 = (new_h - out_h) // 2
            
            if dx1 < new_w and dy1 < new_h:  # Ensure valid crop indices
                frame = frame[dy1:new_h - dy1, dx1:out_w - dx1]
        
        # Final resize to ensure exact output dimensions (handles edge cases)
        if frame.shape[0] != out_h or frame.shape[1] != out_w:
            frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
        
        return frame

    def run(self):
        self.camera.MaxNumBuffer = 500
        self.camera.StartGrabbingMax(
            1_000_000_000, pylon.GrabStrategy_LatestImages)

        # Pre-fill virtualcam buffer with frames for faster app connection
        #print(f"[DEBUG] Starting grab thread at {self.output_res[0]}x{self.output_res[1]}, FPS: {self.fps}")
        #self._fill_buffer(self.max_buffer_frames)
        #print("[DEBUG] Buffer pre-fill complete. Main loop ready.")

        i = 0
        while self.running:
            try:
                # Use lower timeout for faster frame acquisition (reduces latency)
                grabResult = self.camera.RetrieveResult(
                    5, pylon.TimeoutHandling_Return)
                
                if grabResult.GrabSucceeded():
                    start_time = time.perf_counter()
                    
                    raw_frame = grabResult.Array
                    self.frame = self._resize_frame(raw_frame)
                    
                    grabTime_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Track per-frame latency for diagnostics
                    self.last_frame_time.append(grabTime_ms)

                grabResult.Release()
            except Exception:
                pass

            self.virt_cam.send(self.frame)
            self.frame_grabbed.emit(self.frame)

            # Track per-frame latency for diagnostics
            if len(self.last_frame_time) > 100:
                self.last_frame_time = self.last_frame_time[-100:]

            if i % 10 == 0:
                self.avg_fps.emit(self.virt_cam._fps_counter.avg_fps)

            # No sleep - send frame immediately for lowest latency
            # This may cause occasional dropped frames but provides instant response
            self.virt_cam.sleep_until_next_frame()

            i += 1

        # Emit latency diagnostics on shutdown
        if self.last_frame_time:
            avg_latency = sum(self.last_frame_time) / len(self.last_frame_time)
            print(f"[DEBUG] Final average frame grab latency: {avg_latency:.3f}ms")
            self.latency_ms.emit(avg_latency)

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