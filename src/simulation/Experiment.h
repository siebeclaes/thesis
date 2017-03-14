#ifndef _EXPERIMENT_H
#define _EXPERIMENT_H

#include "QuadrupedEnv.h"
#include "Control.h"
#include <vector>

using namespace std;

class Experiment
{
public:
	Experiment(Control *control, bool closed_loop, const char* filename, const int skip_frames, bool render);
	~Experiment();

	bool start(double* time_simulated, double* distance, double* energy_consumed, vector<vector<double>>* action_history, vector<vector<double>>* sensor_history);
private:
	bool mClosedLoop = false;
	Control *mControl;
	QuadrupedEnv *mEnv;
	double duration = 15;
	double amplitude = 30;
};

#endif