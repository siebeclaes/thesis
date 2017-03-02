#ifndef _QUADRUPEDENV_H
#define _QUADRUPEDENV_H

#include "mujoco.h"
#include "glfw3.h"

class QuadrupedEnv
{
public:
	QuadrupedEnv(const char* filename, const int skip_frames, bool render);
	~QuadrupedEnv();

	void setMaxRotation(int max) {maxRotation = max;}
	bool step(double* action);
	double getReward();
	double getTime();
	double getDistance();
	double getEnergyConsumed();
	void getForces(double* forces);
	void getActuatorForces(double* forces);

	void mouse_button(GLFWwindow* window, int button, int act, int mods);
	void mouse_move(GLFWwindow* window, double xpos, double ypos);
	void scroll(GLFWwindow* window, double xoffset, double yoffset);
	void keyboard(GLFWwindow* window, int key, int scancode, int act, int mods);
private:
	mjModel* m;
	mjData* d;

	mjvScene scn;
	mjvCamera cam;
	mjvOption vopt;
	mjvPerturb pert;
	char status[1000] = "";

	char opt_title[1000] = "";
	char opt_content[1000];

	// OpenGL rendering
	int refreshrate;
	const int fontscale = mjFONTSCALE_150;
	mjrContext con;
	float depth_buffer[5120*2880];        // big enough for 5K screen
	unsigned char depth_rgb[1280*720*3];  // 1/4th of screen
	GLFWwindow* window = 0;

	// selection and perturbation
	bool button_left = false;
	bool button_middle = false;
	bool button_right =  false;
	double lastx = 0;
	double lasty = 0;
	int needselect = 0;                 // 0: none, 1: select, 2: center, 3: center and track 
	double window2buffer = 1;           // framebuffersize / windowsize (for scaled video modes)

	bool render_env = false;

	int mSkipFrames = 1;
	double initialX = 0.0;
	double initialY = 0.0;
	int freeJointAddress = 0;
	int maxRotation = 75;

	double energy = 0;
	double y_rotation = 0;

	void initMuJoCo(const char* filename);
	void closeMuJoCo();
	void unitVector(double* v);
	double angleBetween(double* a, double* b);

	void makeoptionstring(const char* name, char key, char* buf);
	void render(GLFWwindow* window);
	void autoscale(GLFWwindow* window);
};


#endif