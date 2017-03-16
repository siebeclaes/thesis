#include "Experiment.h"

#include "stdlib.h"
#include <math.h>
#include <vector>

#define MAX_SIMULATION_TIME 10000.0

using namespace std;

Experiment::Experiment(Control *control, bool closed_loop, const char* modelpath, vector<pair<double, vector<double>>> p_perturbations, const int skip_frames, bool render)
{
	mControl = control;
    mClosedLoop = closed_loop;
	mEnv = new QuadrupedEnv(modelpath, skip_frames, render);
    perturbations = p_perturbations;
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

    double next_perturb_time = MAX_SIMULATION_TIME;
    vector<pair<double, vector<double>>>::iterator perturb_begin = perturbations.begin();
    vector<pair<double, vector<double>>>::iterator perturb_end = perturbations.end();

    vector<double>* perturb_ft = NULL;

    int counter = 0;

    if (perturb_begin != perturb_end)
        next_perturb_time = perturb_begin->first;

    while( mEnv->getTime() < duration)
    {
        if (mClosedLoop)
        {
            mEnv->getForces(forces);
            mControl->getAction(actions, forces, mEnv->getTime());
        } else {
            mControl->getAction(actions, 0, mEnv->getTime());
        }

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

        // Scale actions
        for (int i = 0; i < 4; i++)
            actions[i] = actions[i] * -1 / 180 * 3.141592654;

        // Get perturbation, vector of 6x1, 3 forces, 3 torques, should be applied to xfrc_applied
        if (mEnv->getTime() >= next_perturb_time)
        {
            perturb_ft = &(perturb_begin->second);

            ++perturb_begin;
            if (perturb_begin != perturb_end)
                next_perturb_time = perturb_begin->first;
            else
                next_perturb_time = MAX_SIMULATION_TIME;

        } else {
            perturb_ft = NULL;
        }

        if (!mEnv->step(actions, perturb_ft)){
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