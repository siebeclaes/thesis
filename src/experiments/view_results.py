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
from model_variations import generate_temp_model_file, dict_elementwise_operator, generate_model_variations

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

def eval_wrapper(variables):
    model_file = variables['model_file']
    closed_loop = variables['closed_loop']
    params = variables['params']
    # perturbations = variables['perturbations']
    perturbations = []
    render = variables['render']
    logging = variables['logging']
    return evaluate(model_file, closed_loop, params.tolist(), perturbations, render, logging)

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

        self.model_file = None


    def set_simulation(self, experiment, simulation_id):
        self.experiment = experiment
        self.simulation = experiment['results']['simulations'][simulation_id]
        self.simulation_id = simulation_id
        self.closed_loop = True if self.experiment['type'] == 'closed' else False

        self.show_simulation_info()

        if len(self.simulation['action_history']) == 0 or len(self.simulation['action_history'][0]) == 0:
            # Not simulated with debug yet
            label = QtWidgets.QLabel('No action or sensor history yet')
            self.addWidget(label)

            run_analyze = QtWidgets.QPushButton('Analyze')
            run_analyze.clicked.connect(self.analyze_simulation)
            self.addWidget(run_analyze)

            run_simulation = QtWidgets.QPushButton('View simulation')
            run_simulation.clicked.connect(self.view_simulation)
            self.addWidget(run_simulation)

            filename_layout = QtWidgets.QHBoxLayout()
            self.cpg_params_filename = QtWidgets.QLineEdit()
            filename_layout.addWidget(self.cpg_params_filename)

            dump_params = QtWidgets.QPushButton('Dump cpg params to file')
            dump_params.clicked.connect(self.dump_params)
            filename_layout.addWidget(dump_params)

            self.addLayout(filename_layout)
        else:
            self.show_plots()

    def show_simulation_info(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.add_cpg_params())

        distance = QtWidgets.QLabel('Distance: ' + str(self.simulation['distance']))
        layout.addWidget(distance)
        
        energy = QtWidgets.QLabel('Energy: ' + str(self.simulation['energy']))
        layout.addWidget(energy)

        if 'perturbation' in self.simulation:
            num_perturbations = QtWidgets.QLabel('num_perturbations: ' + str(len(self.simulation['perturbation'])))
            layout.addWidget(num_perturbations)

        self.addLayout(layout)

    def add_cpg_params(self):
        params = self.simulation['cpg_params']
        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self.leg_cpg_param_layout('Front-left', params[0], params[6], params[4], params[7]))
        layout.addLayout(self.leg_cpg_param_layout('Front-right', params[1], params[6], params[4], params[7]))
        layout.addLayout(self.leg_cpg_param_layout('Back-left', params[2], params[6], params[5], params[8]))
        layout.addLayout(self.leg_cpg_param_layout('Back-right', params[3], params[6], params[5], params[8]))

        return layout

    def dump_params(self):
        import pickle
        params = self.simulation['cpg_params']

        filename = self.cpg_params_filename.text()

        with open('../tigrillo/' + str(filename) + '.pickle', 'wb') as f:
            pickle.dump(params, f, 2)

    def leg_cpg_param_layout(self, text, mu, omega, offset, d):
        layout = QtWidgets.QVBoxLayout()

        mu = np.sqrt(mu)
        # d = d * -1 * 30 / 180 * 3.141592654
        omega = omega / 2 / np.pi

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

    def run_simulation(self, render, logging):
        cpg_params = self.simulation['cpg_params']
        self.model_file=None
        if not self.experiment['default_morphology']:
            self.model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
        elif self.experiment['variation_params']:
            model_files, _ = generate_model_variations(self.experiment['default_morphology'], self.experiment['variation_params'], num=1)
            self.model_file = model_files[0]
        elif not self.experiment['delta_dicts']:
            self.model_file = generate_temp_model_file(self.experiment['default_morphology'])
        elif not self.model_file:
            model_config = dict_elementwise_operator(self.experiment['default_morphology'], self.experiment['delta_dicts'][self.simulation['variation_index']])
            self.model_file = generate_temp_model_file(model_config)
        
        perturbations = self.simulation.get('perturbation', [])
        return evaluate(self.model_file, self.closed_loop, cpg_params, perturbations, render, logging)

    def analyze_simulation(self):
        succes, simulated_time, distance, energy_consumed, action_history, sensor_history = self.run_simulation(render=False, logging=True)

        self.simulation['action_history'] = action_history
        self.simulation['sensor_history'] = sensor_history

        self.show_plots()

    def view_simulation(self):
        self.run_simulation(render=True, logging=False)

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

        self.num_variations_label = QtWidgets.QLabel('Num variations: ')
        experiment_details.addWidget(self.num_variations_label)

        self.score_evolution_plot = MyMplCanvas()
        experiment_details.addWidget(self.score_evolution_plot)

        self.show_best_button = QtWidgets.QPushButton('Show best')
        self.show_best_button.clicked.connect(self.show_best)
        experiment_details.addWidget(self.show_best_button)

        self.analyze_variation_button = QtWidgets.QPushButton('Analyze variation performance')
        self.analyze_variation_button.clicked.connect(self.analyze_variation_performance)
        experiment_details.addWidget(self.analyze_variation_button)

        self.analyze_perturb_button = QtWidgets.QPushButton('Analyze perturbation performance')
        self.analyze_perturb_button.clicked.connect(self.perturbation_test)
        experiment_details.addWidget(self.analyze_perturb_button)

        self.experiment_details_widget = QtWidgets.QWidget()
        self.experiment_details_widget.setLayout(experiment_details)

        self.right_panel.addWidget(self.experiment_details_widget)
        self.addLayout(self.right_panel)

    def show_run(self, params):
        model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
        perturbations = []
        render = True
        logging = False
        evaluate(model_file, self.closed_loop, params, perturbations, render, logging)

    def show_best(self):
        params = self.experiment['results']['simulations'][self.experiment['results']['best_id']]['cpg_params']
        self.show_run(params)


    def analyze_variation_performance(self):
        variation_best = [(0,0)] * len(self.experiment['delta_dicts'])

        counter = 0
        for simulation in self.experiment['results']['simulations']:
            variation_index = simulation['variation_index']
            reward = simulation['reward']

            if reward > variation_best[variation_index][0]:
                variation_best[variation_index] = (reward, counter)

            counter += 1

        for i in range(len(variation_best)):
            print('Variation ' + str(i) + ': ' + str(variation_best[i][0]))

    def perturbation_test(self):
        perturbation_params = self.experiment.get('perturbation_params', [])
        num_tests = 20

        if perturbation_params:
            test_perturbations = []
            perturb_cov = np.diag(perturbation_params['perturb_variances'])
            for _ in range(num_tests):
                occurences = np.random.geometric(p=1/perturbation_params['expected_occurences']) - 1 # numpy uses shifted geometric
                perturbations = []
                for i in range(occurences):
                    perturb_time = np.random.random() * 14
                    force_torque = np.random.multivariate_normal(perturbation_params['perturb_means'], perturb_cov)
                    perturbations.append([perturb_time, list(force_torque)])
                test_perturbations.append(perturbations)

            # Test in simulation
            cpg_params = self.experiment['results']['simulations'][self.experiment['results']['best_id']]['cpg_params']
            model_file=None
            if not self.experiment['default_morphology']:
                model_file = '/Users/Siebe/Dropbox/Thesis/Scratches/model.xml'
            elif not self.experiment['delta_dicts']:
                model_file = generate_temp_model_file(self.experiment['default_morphology'])
            elif not self.model_file:
                model_config = dict_elementwise_operator(self.experiment['default_morphology'], self.experiment['delta_dicts'][self.simulation['variation_index']])
                model_file = generate_temp_model_file(model_config)
            
            rewards = []
            for perturbation in test_perturbations:
                succes, simulated_time, distance, energy_consumed, action_history, sensor_history = evaluate(model_file, self.closed_loop, cpg_params, perturbation, False, False)
                reward = 0 if distance < 0 or not succes else (10-0.01*(energy_consumed-self.experiment['E0'])**2)*(distance)
                rewards.append(reward)

            print('Minimum: ' + str(min(rewards)))
            print('Mean: ' + str(sum(rewards)/len(rewards)))
            print('Maximum: ' + str(max(rewards)))
            print('Standard deviation: ' + str(np.std(rewards)))

    def update_experiment(self, experiment):
        self.experiment = experiment
        self.closed_loop = True if self.experiment['type'] == 'closed' else False

        self.simulation_list_widget.clear()

        if 'experiment_tag' in experiment:
            # self.best_score_label.setText(str(experiment['experiment_tag']) + ' - ' + str(experiment['experiment_tag_index']))
            pass

        self.best_score_label.setText(str(experiment['remarks']))

        try:
            num_variations = len(experiment['results']['simulations'][0]['distance'])
        except:
            num_variations = 1

        self.num_variations_label.setText('Num variations: ' + str(num_variations))

        simulation_list = experiment['results']['simulations']

        # sort this list in descending order according to reward
        self.simulation_list = sorted(enumerate(simulation_list), key=lambda x: x[1]['reward'], reverse=True)

        for (simulation_id, simulation) in self.simulation_list:
            reward = simulation['reward']

            item = QtWidgets.QListWidgetItem()
            item.setText(str(simulation['iter']) + ' - ' + str(reward))
            item.setData(QtCore.Qt.UserRole, simulation_id)
            self.simulation_list_widget.addItem(item)

        # Disable analyze buttons
        self.analyze_variation_button.setEnabled(False)
        self.analyze_perturb_button.setEnabled(False)
        if self.experiment.get('delta_dicts', []):
            # Enable analyze variation button
            self.analyze_variation_button.setEnabled(True)
        if self.experiment.get('perturbation_params', []):
            # Enable analyze variation button
            self.analyze_perturb_button.setEnabled(True)

        self.right_panel.setCurrentWidget(self.experiment_details_widget)
        self.score_evolution_plot.axes.cla()
        self.score_evolution_plot.axes.plot(experiment['results']['avg_score_evolution'], 'b', experiment['results']['max_score_evolution'], 'r')
        self.score_evolution_plot.draw()

    def simulation_selected(self, item):
        simulation_id = item.data(QtCore.Qt.UserRole)

        self.simulation_panel = SimulationView()
        self.simulation_panel.set_simulation(self.experiment, simulation_id)
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
        experiments_collection = db['experiments_2']
        for doc in experiments_collection.find({}, {"results.simulations": 0}):
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
        experiments_collection = db['experiments_2']
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
