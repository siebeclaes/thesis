#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include <math.h>

#include "CpgFeedbackControl.h"

int counter = 0;
int main(int argc, const char** argv)
{
	double x[17] = {0.950275, 1.648076, 1.083595, 1.227665, 0.433386, 0.369656, 2.324700, 2.927129, -0.869195, 0.387377, 0.763266, 0.676453, 1.826446, 2.381410, 1.223626, -0.411304};

	vector<double> mu = vector<double>(x, x+4);
    vector<double> o = {x[4], x[4], x[5], x[5]};
    vector<double> omega = {x[6], x[6], x[7], x[7]};
    vector<double> d = {x[8], x[8], x[9], x[9]};
    vector<vector<double>> coupling = {{0, x[10], x[11], x[13]}, {x[10], 0, x[12], x[14]}, {x[11], x[12], 0, x[15]}, {x[13], x[14], x[15], 0}};

    CpgFeedbackControl control(mu, o, omega, d, coupling, x[16]);

    double actions[4];

    for (int i = 0; i<1000; i++)
    {
    	control.getAction(actions, 0, i/1000.0);
    }

	return 0;
}
