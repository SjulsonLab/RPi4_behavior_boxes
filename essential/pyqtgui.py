import sys
import time
import pygame
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg


# ---------------------------
# MODEL
# ---------------------------
class Model:
    def __init__(self):
        self.times = []
        self.values = []
        self.start_time = time.time()

    def add_keypress(self, key_val):
        t = time.time() - self.start_time
        self.times.append(t)
        self.values.append(key_val)

    @property
    def max_time(self):
        return self.times[-1] if self.times else 0.0


# ---------------------------
# VIEW
# ---------------------------
class View(QtWidgets.QWidget):
    update_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()

        self.plot = pg.PlotWidget()
        self.plot.setYRange(0, 3)
        self.plot.setMouseEnabled(x=False, y=False)

        self.scatter = pg.ScatterPlotItem(size=10, pen=None, brush='w')
        self.plot.addItem(self.scatter)

        # Time scrollbar
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setSingleStep(1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.slider)
        self.setLayout(layout)

        self.setWindowTitle("Scrollable Time Plot (pygame + PyQtGraph)")

        # Qt timer drives updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_requested.emit)
        self.timer.start(30)

    def update_plot(self, times, values):
        spots = [{"pos": (t, v)} for t, v in zip(times, values)]
        self.scatter.setData(spots)

    def set_time_window(self, center, width):
        half = width / 2
        self.plot.setXRange(center - half, center + half, padding=0)


# ---------------------------
# PRESENTER
# ---------------------------
class Presenter:
    WINDOW_WIDTH = 10.0  # seconds visible

    def __init__(self, model, view):
        self.model = model
        self.view = view

        view.update_requested.connect(self.update)
        view.slider.valueChanged.connect(self.on_slider_change)

        # pygame input window
        pygame.display.init()
        pygame.display.set_mode((300, 200))
        pygame.display.set_caption("pygame input")
        pygame.init()

    def update(self):
        # ---- pygame input ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                QtWidgets.QApplication.quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.model.add_keypress(1)
                elif event.key == pygame.K_2:
                    self.model.add_keypress(2)

        # ---- update plot data ----
        self.view.update_plot(self.model.times, self.model.values)

        # ---- update slider range ----
        max_t = self.model.max_time
        self.view.slider.setMaximum(int(max_t * 1000))

        # ---- auto-follow latest unless user moved slider ----
        if not self.view.slider.isSliderDown():
            self.view.slider.setValue(int(max_t * 1000))

        self.update_view_range()

    def on_slider_change(self, value):
        self.update_view_range()

    def update_view_range(self):
        center_time = self.view.slider.value() / 1000.0
        self.view.set_time_window(center_time, self.WINDOW_WIDTH)


# ---------------------------
# MAIN
# ---------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)

    model = Model()
    view = View()
    presenter = Presenter(model, view)

    view.resize(800, 400)
    view.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
