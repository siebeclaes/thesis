#include <boost/python.hpp>

#include <iostream>
#include <fstream>

#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include <math.h>


#include "Experiment.h"
#include "CpgFeedbackControl.h"

using namespace std;

namespace bp = boost::python;


int counter = 0;
double total_simulated_time = 0;

class ScopedGILRelease {
public:
    inline ScopedGILRelease() { m_thread_state = PyEval_SaveThread(); }
    inline ~ScopedGILRelease() {
        PyEval_RestoreThread(m_thread_state);
        m_thread_state = NULL;
    }
private:
    PyThreadState* m_thread_state;
};

template <class T>
boost::python::list toPythonList(std::vector<T> vector) {
  typename std::vector<T>::iterator iter;
  boost::python::list list;
  for (iter = vector.begin(); iter != vector.end(); ++iter) {
    list.append(*iter);
  }
  return list;
}

CpgFeedbackControl* getOpenControl(const double *x, const int N)
{
  vector<double> mu = vector<double>(x, x+4);
  vector<double> o = {x[4], x[4], x[5], x[5]};
  vector<double> omega = {x[6], x[6], x[6], x[6]};
  vector<double> d = {x[7], x[7], x[8], x[8]};
  vector<double> phase_offsets = {x[9], x[10], x[11], x[12], x[13], x[14]};

  CpgFeedbackControl* control = new CpgFeedbackControl(mu, o, omega, d, phase_offsets);
  return control;
}

CpgFeedbackControl* getClosedControl(const double *x, const int N)
{
  vector<double> mu = vector<double>(x, x+4);
  vector<double> o = {x[4], x[4], x[5], x[5]};
  vector<double> omega = {x[6], x[6], x[7], x[7]};
  vector<double> d = {x[8], x[8], x[9], x[9]};
  vector<double> phase_offsets = {x[9], x[10], x[11], x[12], x[13], x[14]};
  vector<double> kappa_r = {x[17], x[18], x[19], x[20]};
  vector<double> kappa_phi = {x[21], x[22], x[23], x[24]};
  vector<double> kappa_o = {x[25], x[26], x[27], x[28]};

  const double* weights = x + 29;

  CpgFeedbackControl* control = new CpgFeedbackControl(mu, o, omega, d, phase_offsets, kappa_r, kappa_phi, kappa_o, weights);
  return control;
}

bool _evaluate(const char* model_file, bool closed_loop, const double *x, const int N, bool render, vector<pair<double, vector<double>>> perturbations, double* time_simulated, double* distance, double* energy_consumed, vector<vector<double>>* action_history, vector<vector<double>>* sensor_history)
{
  CpgFeedbackControl* control;

  if (closed_loop)
    control = getClosedControl(x, N);
  else
    control = getOpenControl(x, N);
  
  Experiment exp(control, closed_loop, model_file, perturbations, 5, render);
  bool result = exp.start(time_simulated, distance, energy_consumed, action_history, sensor_history);

  delete(control);
  return result;
};

boost::python::tuple evaluate(const char* model_file, bool closed_loop, bp::list& ls, bp::list& py_perturbations, bool render, bool logging) {
    ScopedGILRelease scoped;

    double time_simulated = 0;
    double distance = 0;
    double energy_consumed = 0;

    vector<vector<double>> action_history;
    vector<vector<double>> sensor_history;

    // Initialize history vectors
    if (logging)
    {
      for (int i = 0; i < 4; i++){
        action_history.push_back(vector<double>());
      }
      for (int i = 0; i < 4; i++){
        sensor_history.push_back(vector<double>());
      }
    }

    bool result = false;
    int num_variables = len(ls);
    double* variables = new double[num_variables];

    // Extract CPG parameters from python list
    for (int i=0; i<num_variables; i++)
      variables[i] = bp::extract<double>(ls[i]);

    // Extract perturbations from python list
    vector<pair<double, vector<double>>> perturbations(len(py_perturbations));
    for (int i = 0; i < len(py_perturbations); i++)
    {
      bp::list t = bp::extract<bp::list>(py_perturbations[i]);
      double application_time = bp::extract<double>(t[0]);
      bp::list py_application_ft = bp::extract<bp::list>(t[1]);

      perturbations[i].first = application_time;

      for (int j = 0; j < len(py_application_ft); j++)
        perturbations[i].second.push_back(bp::extract<double>(py_application_ft[j]));
    }

    if (logging)
    {
      result = _evaluate(model_file, closed_loop, variables, num_variables, render, perturbations, &time_simulated, &distance, &energy_consumed, &action_history, &sensor_history);
    } else {
      result = _evaluate(model_file, closed_loop, variables, num_variables, render, perturbations, &time_simulated, &distance, &energy_consumed, 0, 0);
    }
    

    delete[] variables;

    bp::list action_history_list;
    bp::list sensor_history_list;

    if (logging) 
    {
      for (int i = 0; i < 4; i++)
        action_history_list.append(toPythonList(action_history[i]));
      for (int i = 0; i < 4; i++)
        sensor_history_list.append(toPythonList(sensor_history[i])); 
    }

    return boost::python::make_tuple(result, time_simulated, distance, energy_consumed, action_history_list, sensor_history_list);
}

int get_cpg_version()
{
  return 1;
}

BOOST_PYTHON_MODULE(feedback_cpg)
{
  using namespace boost::python;
  def("get_cpg_version", get_cpg_version);
  def("evaluate", evaluate);
}