
#include "Network.h"
#include <Eigen/Dense>
#include <vector>

using namespace Eigen;
using namespace std;

Network::Network(int inputs, int outputs):m_inputs(inputs), m_outputs(outputs)
{
	m_previous_layer_neurons = inputs;
}

void
Network::add_layer(int hidden)
{
	MatrixXd weights(m_previous_layer_neurons, hidden);
	m_weights.push_back(weights);

	VectorXd values(hidden);
	m_values.push_back(values);

	m_layers++;

	m_previous_layer_neurons = hidden;
}


// Finalize the network, add final output layer weights
void
Network::finalize()
{
	add_layer(m_outputs);
}

VectorXd
Network::calculate_output(VectorXd inputs)
{
	for (int i = 0; i < m_layers; i++)
	{
		VectorXd prev_layer;
		if (i == 0)
			prev_layer = inputs;
		else
			prev_layer = m_values[i - 1];

		VectorXd cell_inputs = prev_layer.transpose() * m_weights[i];

		// Put this through tanh
		m_values[i] = cell_inputs.unaryExpr([](double x) { return tanh(x); });
	}

	return m_values[m_layers - 1];
}

int
Network::get_number_weights()
{
	int num = 0;
	for (int i = 0; i < m_layers; i++)
		num += m_weights[i].rows() * m_weights[i].cols();

	return num;
}

void Network::set_weights(const double* weights)
{
	int pointer = 0;

	for (int i = 0; i < m_layers; i++)
		for (int j = 0; j < m_weights[i].rows(); j++)
			for (int k = 0; k < m_weights[i].cols(); k++)
				m_weights[i](j, k) = weights[pointer++];
}
