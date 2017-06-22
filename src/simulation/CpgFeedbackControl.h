#ifndef _CPGFEEDBACKCONTROL_H
#define _CPGFEEDBACKCONTROL_H

#include "Control.h"
#include <vector>
#include "Network.h"

using namespace std;

class CpgFeedbackControl : public Control
{
public:
	CpgFeedbackControl(vector<double> p_mu, vector<double> p_o, vector<double> p_omega, vector<double> p_d, vector<double> phase_offsets);
	CpgFeedbackControl(vector<double> p_mu, vector<double> p_o, vector<double> p_omega, vector<double> p_d, vector<double> phase_offsets, vector<double> kappa_r, vector<double> kappa_phi, vector<double> kappa_o, const double* weights);
	~CpgFeedbackControl();

	void getAction(double* actions, double* forces, double time);
private:
	vector<double> step_closed_loop(double* forces);
	vector<double> step_open_loop();
	vector<double> step_cpg(vector<double>& Fr, vector<double>& Fphi, vector<double>& Fo);

	bool closed_loop;
	double prev_time = -1;
	double dt = 0.001;

	Network n;

	// CPG parameters
	double gamma = 0.1;			// Speed of convergence
	vector<double> mu; 			// Vector of amplitudes
	vector<double> omega;		// Vector of target frequencies
	vector<double> d;			// Vector of duty factor (stance duration / swing duration)
	vector<vector<double>> coupling;	// Coupling weights for phase differences
	vector<double> o;			// Vector of CPG offsets

	vector<vector<double>> psi; // 2D vector of phase differences between i and j
	
	// Variables CPG
	vector<double> r;			// Vector of CPG radius
	vector<double> phi;			// Vector of CPG frequency
	vector<double> theta;		// Vector of CPG output

	// Feedback weights
	vector<double> kappa_r;		// Vector of feedback weights on radius
	vector<double> kappa_phi;	// Vector of feedback weights on frequency
	vector<double> kappa_o;		// Vector of feedback weights on offset
};

#endif