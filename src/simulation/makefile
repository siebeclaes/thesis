COMMON=-O2 -I../../lib/mjpro140/include -L../../lib/mjpro140/bin -std=c++11 -lstdc++

CMA=-I/usr/local/Cellar/eigen/3.3.0/include/eigen3 -I/Users/Siebe/include/libcmaes -L/Users/Siebe/lib -L/usr/local/lib

# EIGEN=-I/usr/local/Cellar/eigen/3.3.0/include/eigen3
EIGEN=-I../../include/eigen3

BOOST_PYTHON=-I/usr/local/Cellar/boost-python/1.63.0/include -L/usr/local/Cellar/boost-python/1.63.0/lib -I/usr/local/Cellar/boost/1.63.0/include -L/usr/local/Cellar/boost/1.63.0/lib -I/Library/Frameworks/Python.framework/Versions/3.5/include/python3.5m
DYNAMIC_LIB=-shared -undefined dynamic_lookup

feedback_cpg_open_wrapper:
	clang $(COMMON) $(EIGEN) $(BOOST_PYTHON) $(DYNAMIC_LIB) QuadrupedEnv.cpp Network.cpp CpgFeedbackControl.cpp Experiment.cpp feedback_cpg_wrapper.cpp -lmujoco140 -lglfw.3 -lboost_system -lboost_python3 -o ../../build/feedback_cpg.so