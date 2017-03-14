from __future__ import unicode_literals
import sys
import os
import random
import matplotlib
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5 import QtCore, QtWidgets
import numpy as np

from feedback_cpg import evaluate

from numpy import arange, sin, pi, cos
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pymongo import MongoClient

from operator import itemgetter

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

def eval_wrapper(variables):
    model_file = variables['model_file']
    closed_loop = variables['closed_loop']
    params = variables['params']
    render = variables['render']
    logging = variables['logging']
    return evaluate(model_file, closed_loop, params.tolist(), render, logging)

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        self.compute_initial_figure()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass

class SimulationView(QtWidgets.QVBoxLayout):
    def __init__(self, parent=None):
        QtWidgets.QVBoxLayout.__init__(self, parent)

        self.simulation = None


    def set_simulation(self, simulation, experiment_id, simulation_id, closed_loop):
        self.simulation = simulation
        self.experiment_id = experiment_id
        self.simulation_id = simulation_id
        self.closed_loop = closed_loop

        self.add_cpg_params()

        if len(simulation['action_history']) == 0:
            # Not simulated with debug yet
            label = QtWidgets.QLabel('No action or sensor history yet')
            self.addWidget(label)

            run_analyze = QtWidgets.QPushButton('Analyze')
            run_analyze.clicked.connect(self.analyze_simulation)
            self.addWidget(run_analyze)

            run_simulation = QtWidgets.QPushButton('View simulation')
            run_simulation.clicked.connect(self.run_simulation)
            self.addWidget(run_simulation)
        else:
            self.show_plots()

    def add_cpg_params(self):
        params = self.simulation['cpg_params']
        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self.leg_cpg_param_layout('Front-left', params[0], params[6], params[4], params[8]))
        layout.addLayout(self.leg_cpg_param_layout('Front-right', params[1], params[6], params[4], params[8]))
        layout.addLayout(self.leg_cpg_param_layout('Back-left', params[2], params[7], params[5], params[9]))
        layout.addLayout(self.leg_cpg_param_layout('Back-right', params[3], params[7], params[5], params[9]))

        self.addLayout(layout)

    def leg_cpg_param_layout(self, text, mu, omega, offset, d):
        layout = QtWidgets.QVBoxLayout()

        mu = mu * -1 * 30 / 180 * 3.141592654
        d = d * -1 * 30 / 180 * 3.141592654

        title = QtWidgets.QLabel(text)
        layout.addWidget(title)

        amplitude = QtWidgets.QLabel('Amplitude: ' + str(mu))
        layout.addWidget(amplitude)

        omega = QtWidgets.QLabel('Frequency: ' + str(omega))
        layout.addWidget(omega)

        offset = QtWidgets.QLabel('Offset: ' + str(offset))
        layout.addWidget(offset)

        duty = QtWidgets.QLabel('Duty factor: ' + str(d))
        layout.addWidget(duty)

        return layout

    def show_plots(self):
        self.action_history_plot = MyMplCanvas()
        self.addWidget(self.action_history_plot)

        self.sensor_history_plot = MyMplCanvas()
        self.addWidget(self.sensor_history_plot)

        action_history = self.simulation['action_history']
        sensor_history = self.simulation['sensor_history']

        for i in range(len(sensor_history)):
            sensor_history[i] = moving_average(sensor_history[i], 15)

        self.action_history_plot.axes.cla()
        self.action_history_plot.axes.plot(action_history[0], color='blue', label='FL')
        self.action_history_plot.axes.plot(action_history[1], color='red', label='FR')
        self.action_history_plot.axes.plot(action_history[2], color='green', label='BL')
        self.action_history_plot.axes.plot(action_history[3], color='yellow', label='BR')
        self.action_history_plot.axes.legend()
        self.action_history_plot.draw()

        self.sensor_history_plot.axes.cla()
        # self.sensor_history_plot.axes.plot(sensor_history[0], color='blue', label='FL')
        # self.sensor_history_plot.axes.plot(sensor_history[1], color='red', label='FR')
        self.sensor_history_plot.axes.plot(sensor_history[2], color='green', label='BL')
        self.sensor_history_plot.axes.plot(sensor_history[3], color='yellow', label='BR')
        self.sensor_history_plot.axes.legend()
        self.sensor_history_plot.draw()

    def analyze_simulation(self):
        cpg_params = self.simulation['cpg_params']
        model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
        render = False
        logging = True
        succes, simulated_time, distance, energy_consumed, action_history, sensor_history = evaluate(model_file, self.closed_loop, cpg_params, render, logging)

        self.simulation['action_history'] = action_history
        self.simulation['sensor_history'] = sensor_history

        self.show_plots()

    def run_simulation(self):
        cpg_params = self.simulation['cpg_params']
        model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
        render = True
        logging = False
        succes, simulated_time, distance, energy_consumed, action_history, sensor_history = evaluate(model_file, self.closed_loop, cpg_params, render, logging)


class ExperimentView(QtWidgets.QHBoxLayout):
    def __init__(self, parent=None):
        QtWidgets.QHBoxLayout.__init__(self, parent)

        self.simulation_list_widget = QtWidgets.QListWidget()
        self.simulation_list_widget.setMaximumWidth(250)
        self.simulation_list_widget.itemClicked.connect(self.simulation_selected)

        self.addWidget(self.simulation_list_widget)

        self.right_panel = QtWidgets.QStackedLayout()

        experiment_details = QtWidgets.QVBoxLayout()
        self.best_score_label = QtWidgets.QLabel('None')
        experiment_details.addWidget(self.best_score_label)

        self.score_evolution_plot = MyMplCanvas()
        experiment_details.addWidget(self.score_evolution_plot)

        self.show_best_button = QtWidgets.QPushButton('Show best')
        self.show_best_button.clicked.connect(self.show_best)
        experiment_details.addWidget(self.show_best_button)

        experiment_details_widget = QtWidgets.QWidget()
        experiment_details_widget.setLayout(experiment_details)

        self.right_panel.addWidget(experiment_details_widget)
        self.addLayout(self.right_panel)

    def show_run(self, params):
        model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
        render = True
        logging = False
        evaluate(model_file, self.closed_loop, params, render, logging)

    def show_best(self):
        params = self.experiment['results']['simulations'][self.experiment['results']['best_id']]['cpg_params']
        self.show_run(params)

    def update_experiment(self, experiment):
        self.experiment = experiment
        self.closed_loop = True if self.experiment['type'] == 'closed' else False
        self.simulation_list_widget.clear()

        self.best_score_label.setText(str(experiment['remarks']))
        counter = 0

        simulation_list = experiment['results']['simulations']
        # sort this list in descending order according to reward
        self.simulation_list = sorted(simulation_list, key=itemgetter('reward'), reverse=True)

        for simulation in self.simulation_list:
            reward = simulation['reward']
            # reward = 0

            item = QtWidgets.QListWidgetItem()
            item.setText(str(simulation['iter']) + ' - ' + str(reward))
            item.setData(QtCore.Qt.UserRole, counter)
            self.simulation_list_widget.addItem(item)
            counter += 1

        self.score_evolution_plot.axes.cla()
        self.score_evolution_plot.axes.plot(experiment['results']['avg_score_evolution'], 'b', experiment['results']['max_score_evolution'], 'r')
        self.score_evolution_plot.draw()

    def simulation_selected(self, item):
        simulation_id = item.data(QtCore.Qt.UserRole)
        simulation = self.simulation_list[simulation_id]

        self.simulation_panel = SimulationView()
        self.simulation_panel.set_simulation(simulation, self.experiment['_id'], simulation_id, self.closed_loop) # wrong simulation id
        simulation_panel_widget = QtWidgets.QWidget()
        simulation_panel_widget.setLayout(self.simulation_panel)
        self.right_panel.addWidget(simulation_panel_widget)
        self.right_panel.setCurrentWidget(simulation_panel_widget)

class ExperimentsListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        QtWidgets.QListWidget.__init__(self, parent)
        self.setMaximumWidth(250)
        self.experiments = []
        self.load_list()
        self.itemClicked.connect(self.Clicked)
        self.parent = parent

    def load_list(self):
        client = MongoClient('localhost', 27017)
        db = client['thesis']
        experiments_collection = db['experiments']
        for doc in experiments_collection.find({}):
            self.experiments.append(doc)

            item = QtWidgets.QListWidgetItem()
            item.setText(str(doc['timestamp']))
            item.setData(QtCore.Qt.UserRole, doc['_id'])
            self.addItem(item)

    def Clicked(self, item):
        item_id = item.data(QtCore.Qt.UserRole)
        self.parent.experiment_selected(item_id)


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Simulation results viewer - Siebe Claes")

        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)

        self.help_menu.addAction('&About', self.about)

        self.main_widget = QtWidgets.QWidget(self)
        l = QtWidgets.QHBoxLayout(self.main_widget)

        experiments_list = ExperimentsListWidget(self)
        l.addWidget(experiments_list)
        
        self.detail_view = ExperimentView()
        l.addLayout(self.detail_view)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.statusBar().showMessage("Simulation results viewer - Siebe Claes", 2000)

    def experiment_selected(self, experiment_id):
        client = MongoClient('localhost', 27017)
        db = client['thesis']
        experiments_collection = db['experiments']
        experiment = experiments_collection.find_one({'_id': experiment_id})
        self.detail_view.update_experiment(experiment)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QtWidgets.QMessageBox.about(self, "About",
                                    """
                                    View results
                                    """
                                )


qApp = QtWidgets.QApplication(sys.argv)

aw = ApplicationWindow()
aw.setWindowTitle("%s" % progname)
aw.show()
sys.exit(qApp.exec_())
#qApp.exec_()
