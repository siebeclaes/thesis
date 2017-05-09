#include "QuadrupedEnv.h"


#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include <math.h>

#ifdef WITH_RENDER
#include "glfw3.h"
#endif

#define E0 100
#define NUM_ROTATION_SAMPLES 10
#define INITIALIZATION_DURATION 5 // Only start measuring distance and energy after 5 seconds

QuadrupedEnv* env = 0;
bool activated = false;


#ifdef WITH_RENDER
void mouse_button_g(GLFWwindow* window, int button, int act, int mods)
{
    if (env != NULL)
	   env->mouse_button(window, button, act, mods);
}

void mouse_move_g(GLFWwindow* window, double xpos, double ypos)
{
    if (env != NULL)
	   env->mouse_move(window, xpos, ypos);
}
void scroll_g(GLFWwindow* window, double xoffset, double yoffset)
{
    if (env != NULL)
	   env->scroll(window, xoffset, yoffset);
}

void keyboard_g(GLFWwindow* window, int key, int scancode, int act, int mods)
{
    if (env != NULL)
        env->keyboard(window, key, scancode, act, mods);
}
#endif

QuadrupedEnv::QuadrupedEnv(const char* filename, const int skip_frames, bool render)
{

#ifdef WITH_RENDER
	render_env = render;
	if (render_env)
	{
		env = this;
		// init GLFW
	    if (!glfwInit())
	        printf("Error initializing glfw\n");

	    // get refreshrate
	    refreshrate = glfwGetVideoMode(glfwGetPrimaryMonitor())->refreshRate;

	    // multisampling
	    glfwWindowHint(GLFW_SAMPLES, 4);

	    // try stereo if refresh rate is at least 100Hz
	    if( refreshrate>=100 )
	    {
	        glfwWindowHint(GLFW_STEREO, 1);
	        window = glfwCreateWindow(1200, 900, "Simulate", NULL, NULL);
	    }

	    // no stereo: try mono
	    if( !window )
	    {
	        glfwWindowHint(GLFW_STEREO, 0);
	        window = glfwCreateWindow(1200, 900, "Simulate", NULL, NULL);
	    }
	    if( !window )
	    {
	        glfwTerminate();
	        printf("Error window\n");
	    }

	    // make context current, request v-sync on swapbuffers
	    glfwMakeContextCurrent(window);
	    glfwSwapInterval(1);

	    // save window-to-framebuffer pixel scaling (needed for OSX scaling)
	    int width, width1, height;
	    glfwGetWindowSize(window, &width, &height);
	    glfwGetFramebufferSize(window, &width1, &height);
	    window2buffer = (double)width1 / (double)width;

	    // init MuJoCo rendering, get OpenGL info
	    mjv_makeScene(&scn, 1000);
	    mjv_defaultCamera(&cam);
	    mjv_defaultOption(&vopt);
	    mjr_defaultContext(&con);
	    mjr_makeContext(m, &con, fontscale);

        glfwSetKeyCallback(window, keyboard_g);
	    glfwSetCursorPosCallback(window, mouse_move_g);
	    glfwSetMouseButtonCallback(window, mouse_button_g);
	    glfwSetScrollCallback(window, scroll_g);
	}
#endif

	mSkipFrames = skip_frames;
	initMuJoCo(filename);

	// Model is initialized, save the starting position
	int free_joint_id = mj_name2id(m, mjOBJ_JOINT, "gravity");
	freeJointAddress = m->jnt_qposadr[free_joint_id];

	initialX = d->qpos[freeJointAddress];
	initialY = d->qpos[freeJointAddress + 1];
}

QuadrupedEnv::~QuadrupedEnv()
{
	closeMuJoCo();
}

void QuadrupedEnv::initMuJoCo(const char* filename)
{
	// activate
	if (!activated)
	{
		activated = true;
		mj_activate("/Users/Siebe/.mujoco/mjkey.txt");
	}

    // load and compile
    char error[1000] = "Could not load binary model";
    if( strlen(filename)>4 && !strcmp(filename+strlen(filename)-4, ".mjb") )
        m = mj_loadModel(filename, 0, 0);
    else
        m = mj_loadXML(filename, 0, error, 1000);
    if( !m )
        mju_error_s("Load model error: %s", error);

    // make data, run one computation to initialize all fields
    d = mj_makeData(m);

    mj_forward(m, d);

    // printf("Model mass: %f\n", mj_getTotalmass(m))
    torso_body_id = mj_name2id(m, mjOBJ_BODY, "torso");
    torso_xpos_id = mj_name2id(m, mjOBJ_GEOM, "torso_geom");
    // printf("Torso_geom_id: %d\n", torso_xpos_id);

    actuator_indices[0] = mj_name2id(m, mjOBJ_ACTUATOR, "act_1");
    actuator_indices[1] = mj_name2id(m, mjOBJ_ACTUATOR, "act_2");
    actuator_indices[2] = mj_name2id(m, mjOBJ_ACTUATOR, "act_3");
    actuator_indices[3] = mj_name2id(m, mjOBJ_ACTUATOR, "act_4");

    shoulder_indices[0] = mj_name2id(m, mjOBJ_JOINT, "shoulder_1");
    shoulder_indices[1] = mj_name2id(m, mjOBJ_JOINT, "shoulder_2");
    shoulder_indices[2] = mj_name2id(m, mjOBJ_JOINT, "shoulder_3");
    shoulder_indices[3] = mj_name2id(m, mjOBJ_JOINT, "shoulder_4");

    for (int i = 0; i < 4; i++)
        shoulder_qpos_indices[i] = m->jnt_qposadr[shoulder_indices[i]];

    for (int i = 0; i < 4; i++)
        prev_shoulder_qpos[i] = d->qpos[shoulder_qpos_indices[i]];

#ifdef WITH_RENDER
    if (render_env)
    {
    	// re-create custom context
    	mjr_makeContext(m, &con, fontscale);
    	// center and scale view, update scene
	    autoscale(window);
	    mjv_updateScene(m, d, &vopt, &pert, &cam, mjCAT_ALL, &scn);
    }
#endif
}

void QuadrupedEnv::closeMuJoCo()
{
	mj_deleteData(d);
    mj_deleteModel(m);
    d = NULL;
    m = NULL;

#ifdef WITH_RENDER
    if (render_env) 
    {
    	mjr_freeContext(&con);
        mjv_freeScene(&scn);
        glfwTerminate();
        mj_deactivate();
        activated = false;
        env = NULL;
    }
#endif
    // mj_deactivate();
}

bool QuadrupedEnv::step(double* action, vector<double>* perturb_ft)
{
	bool survived = true;

    // Apply the control
	for (int i = 0; i < 4; i++)
		d->ctrl[i] = action[i];

    // Clear old perturbations
    mju_zero(d->xfrc_applied, 6*m->nbody);

    // Apply perturbations if any
    if (perturb_ft)
    {
        // printf("Applying perturbation!!! \n x: %f\n", *(perturb_ft->begin()));
        std::copy((*perturb_ft).begin(), (*perturb_ft).end(), &d->xfrc_applied[6*torso_body_id]);
    }

    // Step the simulation mSkipFrames times
    // This advances the simulation while maintaining the same input
	for (int i = 0; i < mSkipFrames; i++)
		mj_step(m, d);

    // Update consumed energy after initialization phase
    if (d->time > INITIALIZATION_DURATION)
    {
        for (int i = 0; i < 4; i++)
        {
            double current_shoulder_qpos = d->qpos[shoulder_qpos_indices[i]];
            double theta = mju_abs(current_shoulder_qpos - prev_shoulder_qpos[i]);
            prev_shoulder_qpos[i] = current_shoulder_qpos;

            // Scale torques by scaling_factor ^ 2
            energy += mju_abs(d->actuator_force[i] / 100 * theta);
        } 
    }    

    // Get position samples to compensate direction after initialization phase
    if (!pos_sample_1_done && d->time > INITIALIZATION_DURATION)
    {
        if (rotation_sample_counter < NUM_ROTATION_SAMPLES)
        {
            // Check current rotation. If it is too high, abort
            double* rotation_frame_2 = &d->xmat[9];
            double* vr_2 = &rotation_frame_2[3];
            double rr[3] = {0,1,0};
            rotation_after_init += angleBetween(vr_2, rr);

            rotation_sample_counter++;
        }

        if (rotation_sample_counter == NUM_ROTATION_SAMPLES)
        {
            rotation_after_init /= NUM_ROTATION_SAMPLES;

            pos_sample_1_x = d->qpos[freeJointAddress];
            pos_sample_1_y = d->qpos[freeJointAddress + 1];
            pos_sample_1_done = true;
        }
    }

    // Check for warnings (they indicate numerical instabilities)
	bool warnings = false;

	for (int i = 0; i < mjNWARNING; i++)
	{
		if (d->nwarning[i] > 0)
			warnings = true;
	}

	if (warnings)
	{
		printf("Warning generated and detected! Aborting this run...\n");
		return false;
	}

    double gyro_x = d->sensordata[12];
    double gyro_y = d->sensordata[13];
    double gyro_z = d->sensordata[14];

    y_rotation += mju_abs(gyro_y);

    // printf("Orientation: %f %f %f\n", gyro_x, gyro_y, gyro_z);

    // Check current rotation. If it is too high, abort
	double* rotation_frame = &d->xmat[9];
	double* vr = &rotation_frame[6];
	double r[3] = {0,0,1};
	double rotation = angleBetween(vr, r) / 3.141592654 * 180;

    // printf("Moment arm %d: %f\n", 0, d->actuator_moment[m->nv*0+6]);
    // printf("Moment arm %d: %f\n", 1, d->actuator_moment[m->nv*1+8]);
    // printf("Moment arm %d: %f\n", 2, d->actuator_moment[m->nv*2+10]);
    // printf("Moment arm %d: %f\n", 3, d->actuator_moment[m->nv*3+12]);

	if (fabs(rotation) > maxRotation)
	{
		survived = false;
		// printf("Tilted too far, time: %f\n", d->time);
	}

    // printf("torso height: %f\n", d->geom_xpos[torso_xpos_id+2]);
    // Check for torso too low
    if (d->geom_xpos[torso_xpos_id+2] < -0.7)
    {
        survived = false;
    }

#ifdef WITH_RENDER
    // Rendering stuff
	if (render_env)
	{
        if (stop_simulation)
            return false;
		render(window);
		glfwPollEvents();
	}
#endif

	return survived;
}

double QuadrupedEnv::getTime()
{
	return d->time;
}


double QuadrupedEnv::getDistance()
{
    double current_x = d->qpos[freeJointAddress] - pos_sample_1_x;

    // Change direction of y-axis.
    // The model generator creates the model with the robot head pointing along the negative y-axis.
    // Calculations are easier when the robot starts along the positive y-axis
    double current_y = (d->qpos[freeJointAddress + 1] - pos_sample_1_y) * -1;

    double end_y_rotated = mju_cos(rotation_after_init) * current_y - mju_sin(rotation_after_init) * current_x;

    double dy = end_y_rotated;
    return dy / 10;
}

double QuadrupedEnv::getEnergyConsumed()
{
    return energy;
}

void QuadrupedEnv::unitVector(double* v)
{
	double norm = sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);
	v[0] /= norm;
	v[1] /= norm;
	v[2] /= norm;
}

double QuadrupedEnv::angleBetween(double* a, double* b)
{
	double v1[3] = {a[0], a[1], a[2]};
	double v2[3] = {b[0], b[1], b[2]};

	unitVector(v1);
	unitVector(v2);

	double dot_product = 0.0;
	for (int i = 0; i < 3; i++)
		dot_product += v1[i] * v2[i];

	if (dot_product < -1)
		dot_product = -1;
	else if (dot_product > 1)
		dot_product = 1;

	return acos(dot_product);
}

void QuadrupedEnv::getForces(double* forces)
{
	for (int i = 0; i < 4; i++)
    {
        double f1 = d->sensordata[3*i];
        double f2 = d->sensordata[3*i+1];
        double f3 = d->sensordata[3*i+2];

        double f = sqrt(f1*f1 + f2*f2 + f3*f3);
        forces[i] = f;
    }
}

void QuadrupedEnv::getActuatorForces(double* forces)
{
    // mj_fwdActuation(m, d);
    for (int i = 0; i < 4; i++)
    {
        forces[i] = d->actuator_force[i];
    }
}

#ifdef WITH_RENDER
// Rendering stuff
// center and scale view
void QuadrupedEnv::autoscale(GLFWwindow* window)
{
    // autoscale
    cam.lookat[0] = m->stat.center[0];
    cam.lookat[1] = m->stat.center[1];
    cam.lookat[2] = m->stat.center[2];
    cam.distance = 1.5 * m->stat.extent;

    // set to free camera
    cam.type = mjCAMERA_FREE;
}

// make option string
void QuadrupedEnv::makeoptionstring(const char* name, char key, char* buf)
{
    int i=0, cnt=0;

    // copy non-& characters
    while( name[i] && i<50 )
    {
        if( name[i]!='&' )
            buf[cnt++] = name[i];

        i++;
    }

    // finish
    buf[cnt] = ' ';
    buf[cnt+1] = '(';
    buf[cnt+2] = key;
    buf[cnt+3] = ')';
    buf[cnt+4] = 0;
}

// render
void QuadrupedEnv::render(GLFWwindow* window)
{
    // past data for FPS calculation
    static double lastrendertm = 0;

    // get current framebuffer rectangle
    mjrRect rect = {0, 0, 0, 0};
    glfwGetFramebufferSize(window, &rect.width, &rect.height);

    // no model: empty screen
    if( !m )
    {
        mjr_rectangle(rect, 0.2f, 0.3f, 0.4f, 1);
        mjr_overlay(mjFONT_NORMAL, mjGRID_TOPLEFT, rect, "Drag-and-drop model file here", 0, &con);

        // swap buffers
        glfwSwapBuffers(window); 
        return;
    }

    // timing satistics
    lastrendertm = glfwGetTime();

    // update scene
    mjv_updateScene(m, d, &vopt, &pert, &cam, mjCAT_ALL, &scn);

    // render
    mjr_render(rect, &scn, &con);

    // show options
    if( true )
    {
        int i;
        char buf[100];

        // fill titles on first pass
        if( !opt_title[0] )
        {
            for( i=0; i<mjNRNDFLAG; i++)
            {
                makeoptionstring(mjRNDSTRING[i][0], mjRNDSTRING[i][2][0], buf);
                strcat(opt_title, buf);
                strcat(opt_title, "\n");
            }
            for( i=0; i<mjNVISFLAG; i++)
            {
                makeoptionstring(mjVISSTRING[i][0], mjVISSTRING[i][2][0], buf);
                strcat(opt_title, buf);
                if( i<mjNVISFLAG-1 )
                    strcat(opt_title, "\n");
            }
        }

        // fill content
        opt_content[0] = 0;
        for( i=0; i<mjNRNDFLAG; i++)
        {
            strcat(opt_content, scn.flags[i] ? " + " : "   ");
            strcat(opt_content, "\n");
        }
        for( i=0; i<mjNVISFLAG; i++)
        {
            strcat(opt_content, vopt.flags[i] ? " + " : "   ");
            if( i<mjNVISFLAG-1 )
                strcat(opt_content, "\n");
        }

        // show
        mjr_overlay(mjFONT_NORMAL, mjGRID_TOPRIGHT, rect, opt_title, opt_content, &con);
    }

    // swap buffers
    glfwSwapBuffers(window); 
}

// mouse button
void QuadrupedEnv::mouse_button(GLFWwindow* window, int button, int act, int mods)
{
    // past data for double-click detection
    static int lastbutton = 0;
    static double lastclicktm = 0;

    // update button state
    button_left =   (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT)==GLFW_PRESS);
    button_middle = (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_MIDDLE)==GLFW_PRESS);
    button_right =  (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_RIGHT)==GLFW_PRESS);

    // update mouse position
    glfwGetCursorPos(window, &lastx, &lasty);

    // require model
    if( !m )
        return;

    // set perturbation
    int newperturb = 0;
    if( act==GLFW_PRESS && (mods & GLFW_MOD_CONTROL) && pert.select>0 )
    {
        // right: translate;  left: rotate
        if( button_right )
            newperturb = mjPERT_TRANSLATE;
        else if( button_left )
            newperturb = mjPERT_ROTATE;

        // perturbation onset: reset reference
        if( newperturb && !pert.active )
            mjv_initPerturb(m, d, &scn, &pert);
    }
    pert.active = newperturb;

    // detect double-click (250 msec)
    if( act==GLFW_PRESS && glfwGetTime()-lastclicktm<0.25 && button==lastbutton )
    {
        if( button==GLFW_MOUSE_BUTTON_LEFT )
            needselect = 1;
        else if( mods & GLFW_MOD_CONTROL )
            needselect = 3;
        else
            needselect = 2;

        // stop perturbation on select
        pert.active = 0;
    }

    // save info
    if( act==GLFW_PRESS )
    {
        lastbutton = button;
        lastclicktm = glfwGetTime();
    }
}


// mouse move
void QuadrupedEnv::mouse_move(GLFWwindow* window, double xpos, double ypos)
{
    // no buttons down: nothing to do
    if( !button_left && !button_middle && !button_right )
        return;

    // compute mouse displacement, save
    double dx = xpos - lastx;
    double dy = ypos - lasty;
    lastx = xpos;
    lasty = ypos;

    // require model
    if( !m )
        return;

    // get current window size
    int width, height;
    glfwGetWindowSize(window, &width, &height);

    // get shift key state
    bool mod_shift = (glfwGetKey(window, GLFW_KEY_LEFT_SHIFT)==GLFW_PRESS ||
                      glfwGetKey(window, GLFW_KEY_RIGHT_SHIFT)==GLFW_PRESS);

    // determine action based on mouse button
    mjtMouse action;
    if( button_right )
        action = mod_shift ? mjMOUSE_MOVE_H : mjMOUSE_MOVE_V;
    else if( button_left )
        action = mod_shift ? mjMOUSE_ROTATE_H : mjMOUSE_ROTATE_V;
    else
        action = mjMOUSE_ZOOM;

    // move perturb or camera
    if( pert.active )
        mjv_movePerturb(m, d, action, dx/height, dy/height, &scn, &pert);
    else
        mjv_moveCamera(m, action, dx/height, dy/height, &scn, &cam);
}


// scroll
void QuadrupedEnv::scroll(GLFWwindow* window, double xoffset, double yoffset)
{
    // require model
    if( !m )
        return;

    // scroll: emulate vertical mouse motion = 5% of window height
    mjv_moveCamera(m, mjMOUSE_ZOOM, 0, -0.05*yoffset, &scn, &cam);
}

// keyboard
void QuadrupedEnv::keyboard(GLFWwindow* window, int key, int scancode, int act, int mods)
{
    int n;

    // require model
    if( !m )
        return;

    // do not act on release
    if( act==GLFW_RELEASE )
        return;

    switch( key )
    {
    case 256: // ESC key
        stop_simulation = true;
        break;
    default:
        // toggle visualization flag
        for( int i=0; i<mjNVISFLAG; i++ )
            if( key==mjVISSTRING[i][2][0] )
                vopt.flags[i] = !vopt.flags[i];

        // toggle rendering flag
        for( int i=0; i<mjNRNDFLAG; i++ )
            if( key==mjRNDSTRING[i][2][0] )
                scn.flags[i] = !scn.flags[i];

        // toggle geom/site group
        for( int i=0; i<mjNGROUP; i++ )
            if( key==i+'0')
            {
                if( mods & GLFW_MOD_SHIFT )
                    vopt.sitegroup[i] = !vopt.sitegroup[i];
                else
                    vopt.geomgroup[i] = !vopt.geomgroup[i];
            }
    }
}
#endif // WITH_RENDER

