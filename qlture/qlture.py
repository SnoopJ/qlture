import random
import sys
import time
from functools import partial, wraps
from itertools import chain, count, cycle
from pathlib import Path

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow

HERE = Path(__file__).parent.resolve()

def snowy(minval: int=0, maxval: int=255):
    def drawer(t, width, height):
        arr = np.random.randint(minval, maxval, size=(width, height), dtype=np.uint8)
        arr = arr[..., np.newaxis] * [1, 1, 1]
        w, h, ch = arr.shape
        img = QImage(arr, w, h, QImage.Format_RGB888)
        
        return img

    return drawer

def on_grid(func):
    @wraps(func)
    def _wrapper(width, height):
        x = np.arange(width) - width/2
        y = np.arange(height) - height/2
        X, Y = np.meshgrid(x, y, indexing='ij')
        return func(X, Y)
    return _wrapper

def random_coordsum():
    xweight = random.uniform(-1, 1)
    yweight = random.uniform(-1, 1)
    def _func(X, Y):
        return X*xweight + Y*yweight
    return _func

def sumofsquares(X, Y):
    return X**2 + Y**2

def wave(func, k=1, T=1.5, phase=0, rgb=[1,1,1]):
    @wraps(func)
    def _wrapper(t, width, height):
        spatial = func(width, height)
        imgdata = np.sin(spatial/k + t/T + phase)*255
        w, h = imgdata.shape
        if imgdata.ndim == 2:
            imgdata = imgdata[..., np.newaxis] * rgb

        img = QImage(imgdata.astype(np.uint8), w, h, QImage.Format_RGB888)

        return img

    return _wrapper

def random_wave(func, mink=1e-3, maxk=1000, minT=0.2, maxT=2):
    k = random.uniform(mink, maxk)
    T = random.uniform(minT, maxT)
    return wave(func, k=k, T=T, rgb=[1, 0, 0])

def fps_to_msec(fps: int):
    return round(1/fps * 1000)

# *_DT times in msec
NORMAL_DRAW_DT = fps_to_msec(30)
SNOW_DRAW_DT = fps_to_msec(12)
NORMAL_SWITCH_DT = 2000
SNOW_SWITCH_DT = 200

def artists():
    while True:
        yield random.choice([
            random_wave(on_grid(sumofsquares), mink=1e-3, maxk=10),
            random_wave(on_grid(random_coordsum())),
        ])
        yield snowy(minval=random.randint(0, 128), maxval=random.randint(128, 255))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = "qlture"
        self.top = 150
        self.left = 150
        self.width = 500
        self.height = 500
        self.setWindowTitle(self._title)
        self.setGeometry(self.top, self.left, self.width, self.height)
        self.create_artists()
        self.run_on_timer(self.redraw, NORMAL_DRAW_DT)
        self.run_on_timer(self._next_artist, NORMAL_SWITCH_DT)
        self.paused = False
        self.redraw()
        self.paused = True

    def _next_artist(self):
        self.drawer = next(self.artists)
        switch_timer = self._next_artist.timer
        draw_timer = self.redraw.timer
        if draw_timer.interval() == NORMAL_DRAW_DT:
            switch_timer.setInterval(SNOW_SWITCH_DT)
            draw_timer.setInterval(SNOW_DRAW_DT)
        else:
            draw_timer.setInterval(NORMAL_DRAW_DT)
            switch_timer.setInterval(NORMAL_SWITCH_DT)

    def create_artists(self):
        self.artists = iter(artists())
        self.drawer = next(self.artists)

    def run_on_timer(self, func, interval, singleShot=False):
        timer = QTimer()
        func.__dict__["timer"] = timer

        timer.setSingleShot(singleShot)
        timer.setInterval(interval)
        timer.timeout.connect(func)
        timer.start()

    def redraw(self):
        if self.paused:
            return
        self.pixmap = QPixmap(self.drawer(time.time(), self.width, self.height))
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.setCentralWidget(self.label)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, newtitle):
        self._title = newtitle
        self.setWindowTitle(self._title)

    def mousePressEvent(self, event):
        self.drawer = next(self.artists)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_P:
            self.paused = not self.paused
        elif event.key() == Qt.Key_Q:
            sys.exit(0)
            


def main():
    App = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(App.exec())
