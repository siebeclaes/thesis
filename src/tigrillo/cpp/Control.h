#ifndef _CONTROL_H
#define _CONTROL_H

class Control
{
public:
	virtual void getAction(double* actions, double* forces, double time) = 0;
};

#endif