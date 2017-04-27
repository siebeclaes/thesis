#include "stdio.h"
#include "stdlib.h"
#include "string.h"

#include <math.h>
#include <vector>
#include <iostream>
#include <Eigen/Dense>

#include "CpgFeedbackControl.h"

using namespace Eigen;
using namespace std;

#define PI 3.141492654

#define CPG_INIT 10000

CpgFeedbackControl::CpgFeedbackControl(vector<double> p_mu, vector<double> p_o, vector<double> p_omega, vector<double> p_d, vector<double> phase_offsets)
{
    mu = p_mu;
    o = p_o;
    omega = p_omega;
    d = p_d;
    coupling = {{0,1,1,1}, {1,0,1,1}, {1,1,0,1}, {1,1,1,0}};

    r = vector<double>(4,1);
    phi = vector<double>(4,1);
    theta = vector<double>(4,0);
    kappa_r = vector<double>(4,1);
    kappa_phi = vector<double>(4,1);
    kappa_o = vector<double>(4,1);

    closed_loop = false;

    double a = phase_offsets[0];
    double b = phase_offsets[1];
    double c = phase_offsets[2];
    double d = a-b;
    double e = a-c;
    double f = b-c;

    psi = {{0, a, b, c}, {-1*a, 0, d, e}, {-1*b, -1*d, 0, f}, {-1*c, -1*e, -1*f, 0}};

    // for (int i = 0; i < CPG_INIT; i++)
    //     step_open_loop();
}

CpgFeedbackControl::CpgFeedbackControl(vector<double> p_mu, vector<double> p_o, vector<double> p_omega, vector<double> p_d, vector<double> phase_offsets, vector<double> p_kappa_r, vector<double> p_kappa_phi, vector<double> p_kappa_o, const double* p_weights)
{
    mu = p_mu;
    o = p_o;
    omega = p_omega;
    d = p_d;
    coupling = {{0,1,1,1}, {1,0,1,1}, {1,1,0,1}, {1,1,1,0}};

    r = vector<double>(4,1);
    phi = vector<double>(4,1);
    theta = vector<double>(4,0);

    kappa_r = p_kappa_r;
    kappa_phi = p_kappa_phi;
    kappa_o = p_kappa_o;

    closed_loop = true;
    double a = phase_offsets[0];
    double b = phase_offsets[1];
    double c = phase_offsets[2];
    double d = phase_offsets[3];
    double e = phase_offsets[4];
    double f = phase_offsets[5];

    psi = {{0, a, b, c}, {-1*a, 0, d, e}, {-1*b, -1*d, 0, f}, {-1*c, -1*e, -1*f, 0}};

    n = Network(4, 12);
    n.finalize();

    n.set_weights(p_weights);
}

CpgFeedbackControl::~CpgFeedbackControl()
{

}

vector<double> CpgFeedbackControl::step_closed_loop(double* forces)
{
    Map<VectorXd> network_inputs(forces, 4);

    VectorXd cpg_parameters = n.calculate_output(network_inputs);

    vector<double> Fr;
    vector<double> Fphi;
    vector<double> Fo;

    for (int i = 0; i < 4; i++)
    {
        Fr.push_back(cpg_parameters[i]);
        Fphi.push_back(cpg_parameters[4 + i]);
        Fo.push_back(cpg_parameters[8 + i]);
    }

    return step_cpg(Fr, Fphi, Fo);
}

vector<double> CpgFeedbackControl::step_open_loop()
{
    vector<double> Fr(4,0);
    vector<double> Fphi(4,0);
    vector<double> Fo(4,0);

    return step_cpg(Fr, Fphi, Fo);
}

vector<double> CpgFeedbackControl::step_cpg(vector<double>& Fr, vector<double>& Fphi, vector<double>& Fo)
{
    vector<double> actions;
    for (int i = 0; i < 4; i++)
    {
        double d_r = gamma * (mu[i] + kappa_r[i] * Fr[i] - r[i] * r[i]) * r[i];
        double d_phi = omega[i] + kappa_phi[i] * Fphi[i];
        double d_o = kappa_o[i] * Fo[i];

        // Add phase coupling
        for (int j = 0; j < 4; j++)
        {
            d_phi += coupling[i][j] * sin(phi[j] - phi[i] - psi[i][j]);
        }

        r[i] += dt * d_r;
        phi[i] += dt * d_phi;
        o[i] += dt * d_o;

        double two_pi = 2 * 3.141592654;

        double phi_L = 0;
        double phi_2pi = fmod(phi[i], two_pi);
        if (phi_2pi < two_pi * d[i])
            phi_L = phi_2pi / (2 * d[i]);
        else
            phi_L = (phi_2pi + two_pi * (1 - 2 * d[i])) / (2 * (1 - d[i]));

        double action = r[i] * cos(phi_L) + o[i];
        actions.push_back(action);
    }

    return actions;
    
}

void CpgFeedbackControl::getAction(double* actions, double* forces, double time)
{
    int num_steps = (int) (time / dt) - prev_time;
    // printf("time: %f \t Num steps: %d\n", time, num_steps);
    vector<double> new_actions;

    for (int i=0; i<num_steps; i++)
    {
        if (closed_loop)
            new_actions = step_closed_loop(forces);
        else
            new_actions = step_open_loop();
    }

    prev_time = (int) (time/dt);

    for (int i = 0; i < 4; i++)
    	actions[i] = new_actions[i];
}
