#include <boost/python.hpp>

#include <iostream>
#include <fstream>

#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include <math.h>


#include "OpenLoopExperiment.h"
#include "CpgFeedbackControl.h"

using namespace std::chrono;
using namespace std;


int counter = 0;
double total_simulated_time = 0;

high_resolution_clock::time_point start_time;

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

double _evaluate(const double *x, const int N, bool render, double* time_simulated, double* distance, double* energy_consumed, vector<vector<double>>* action_history, vector<vector<double>>* sensor_history)
{

  vector<double> mu = vector<double>(x, x+4);
  vector<double> o = {x[4], x[4], x[5], x[5]};
  vector<double> omega = {x[6], x[6], x[7], x[7]};
  vector<double> d = {x[8], x[8], x[9], x[9]};
  vector<vector<double>> coupling = {{0, x[10], x[11], x[13]}, {x[10], 0, x[12], x[14]}, {x[11], x[12], 0, x[15]}, {x[13], x[14], x[15], 0}};

  CpgFeedbackControl control(mu, o, omega, d, coupling, x[16]);

  OpenLoopExperiment ole(&control, "/Users/Siebe/Dropbox/Thesis/Scratches/model_large.xml", 5, render);
  double result = ole.start(time_simulated, distance, energy_consumed, action_history, sensor_history);

  return result;
};

boost::python::tuple evaluate(boost::python::list& ls, bool render, bool logging) {
    ScopedGILRelease scoped;

    double time_simulated = 0;
    double distance = 0;
    double energy_consumed = 0;

    vector<vector<double>> action_history;
    vector<vector<double>> sensor_history;

    if (logging)
    {
      for (int i = 0; i < 4; i++){
        action_history.push_back(vector<double>());
      }
      for (int i = 0; i < 4; i++){
        sensor_history.push_back(vector<double>());
      }
    }

    double result = 0;
    int num_variables = len(ls);
    double* variables = new double[num_variables];

    for (int i=0; i<num_variables; i++)
      variables[i] = boost::python::extract<double>(ls[i]);

    if (logging)
    {
      result = _evaluate(variables, num_variables, render, &time_simulated, &distance, &energy_consumed, &action_history, &sensor_history);
    } else {
      result = _evaluate(variables, num_variables, render, &time_simulated, &distance, &energy_consumed, 0, 0);
    }
    

    delete[] variables;

    boost::python::list action_history_list;
    boost::python::list sensor_history_list;

    if (logging) 
    {
      for (int i = 0; i < 4; i++)
        action_history_list.append(toPythonList(action_history[i]));
      for (int i = 0; i < 4; i++)
        sensor_history_list.append(toPythonList(sensor_history[i])); 
    }

    return boost::python::make_tuple(result, time_simulated, distance, energy_consumed, action_history_list, sensor_history_list);
}

BOOST_PYTHON_MODULE(feedback_cpg_open)
{
  def("evaluate", evaluate);
}