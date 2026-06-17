import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from grab_thread import GrabThread
from preview_thread import PreviewThread
from config_gui import ConfigGui

if __name__ == '__main__':
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon('pylon_webcam_icon_64.png'))
    grab_thread = GrabThread()
    preview_thread = PreviewThread()
    grab_thread.frame_grabbed.connect(preview_thread.send_frame)
    gui = ConfigGui(grab_thread, preview_thread)

    sys.exit(app.exec_())
