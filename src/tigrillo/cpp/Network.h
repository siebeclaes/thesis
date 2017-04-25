#ifndef _NETWORK_H
#define _NETWORK_H

#include <Eigen/Dense>
#include <vector>

using namespace Eigen;
// using namespace std;

class Network
{
public:
	Network(){}
	Network(int inputs, int outputs);
	void add_layer(int hidden);
	void finalize();
	VectorXd calculate_output(VectorXd inputs);
	int get_number_weights();
	void set_weights(const double* weights);

private:
	std::vector<MatrixXd> m_weights;
	std::vector<VectorXd> m_values;
	int m_inputs;
	int m_outputs;
	int m_layers = 0;

	int m_previous_layer_neurons;
};

#endif