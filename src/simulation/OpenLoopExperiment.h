#ifndef _OPENLOOPEXP_H
#define _OPENLOOPEXP_H

#include "QuadrupedEnv.h"
#include "Control.h"
#include <vector>

using namespace std;

class OpenLoopExperiment
{
public:
	OpenLoopExperiment(Control *control, const char* filename, const int skip_frames, bool render);
	~OpenLoopExperiment();

	double start(double* time_simulated, double* distance, double* energy_consumed, vector<vector<double>>* action_history, vector<vector<double>>* sensor_history);
private:
	Control *mControl;
	QuadrupedEnv *mEnv;
	double duration = 15;
	double amplitude = 30;
};

#endif