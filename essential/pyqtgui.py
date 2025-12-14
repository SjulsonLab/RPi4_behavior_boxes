import sys
import time
import pygame
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg


class Model:
    MAX_POINTS = 20

    def __init__(self):
        self.times = []
        self.values = []
        self.start_time = time.time()

    def add_keypress(self, key_val):
        t = time.time() - self.start_time
        self.times.append(t)
        self.values.append(key_val)

        # keep only last 20
        if len(self.times) > self.MAX_POINTS:
            self.times = self.times[-self.MAX_POINTS:]
            self.values = self.values[-self.MAX_POINTS:]


class View(QtWidgets.QMainWindow):
    update_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()

        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)

        self.scatter = pg.ScatterPlotItem(size=10, pen=None, brush='w')
        self.plot_widget.addItem(self.scatter)

        self.plot_widget.setYRange(0, 3)

        self.setWindowTitle("PyQtGraph + pygame MVP (last 20 keypresses)")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_requested.emit)
        self.timer.start(30)

    def update_plot(self, times, values):
        spots = [{"pos": (t, v)} for t, v in zip(times, values)]
        self.scatter.setData(spots)

        if len(times) > 1:
            xmin = min(times)
            xmax = max(times)
            self.plot_widget.setXRange(xmin - 0.2, xmax + 0.2, padding=0)


class Presenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view

        view.update_requested.connect(self.update)

        pygame.display.init()
        pygame.display.set_mode((300, 200))
        pygame.display.set_caption("pygame input window")
        pygame.init()

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                QtWidgets.QApplication.quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.model.add_keypress(1)
                elif event.key == pygame.K_2:
                    self.model.add_keypress(2)

        self.view.update_plot(self.model.times, self.model.values)


def main():
    app = QtWidgets.QApplication(sys.argv)
    view = View()
    # model = Model()
    # presenter = Presenter(model, view)
    # view.show()
    # sys.exit(app.exec_())  # works on PyQt5


if __name__ == "__main__":
    main()
