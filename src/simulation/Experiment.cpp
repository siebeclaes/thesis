#include "Experiment.h"

#include "stdlib.h"
#include <math.h>
#include <vector>

using namespace std;

Experiment::Experiment(Control *control, bool closed_loop, const char* modelpath, const int skip_frames, bool render)
{
	mControl = control;
    mClosedLoop = closed_loop;
	mEnv = new QuadrupedEnv(modelpath, skip_frames, render);
}

Experiment::~Experiment()
{
	delete(mEnv);
}

bool Experiment::start(double* time_simulated, double* distance, double* energy_consumed, vector<vector<double>>* action_history, vector<vector<double>>* sensor_history)
{
	// main loop
	double actions[4] = {0};
    double force_history[10][4] = {0};
    double forces[4] = {0};

    int counter = 0;

    while( mEnv->getTime() < duration)
    {
        if (mClosedLoop)
        {
            mEnv->getForces(forces);
            mControl->getAction(actions, forces, mEnv->getTime());
        } else {
            mControl->getAction(actions, 0, mEnv->getTime());
        }

        // Scale actions
        for (int i = 0; i < 4; i++)
            actions[i] = actions[i] * -1 * amplitude / 180 * 3.141592654;

        // Logging
        if (action_history) 
        {
            for (int i = 0; i < 4; i++)
                (*action_history)[i].push_back(actions[i]);
        }

        if (sensor_history) 
        {
            mEnv->getForces(forces);
            for (int i = 0; i < 4; i++)
                (*sensor_history)[i].push_back(forces[i]);
        }

        if (!mEnv->step(actions)){
            *time_simulated = mEnv->getTime();
            *distance = mEnv->getDistance();
            *energy_consumed = mEnv->getEnergyConsumed();
        	return false;
        }
    }

    *time_simulated = mEnv->getTime();
    *distance = mEnv->getDistance();
    *energy_consumed = mEnv->getEnergyConsumed();
    return true;
}