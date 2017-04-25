COMMON=-O2 -std=c++11 -lstdc++

EIGEN=-I/usr/local/Cellar/eigen/3.3.0/include/eigen3

BOOST_PYTHON=-I/usr/local/Cellar/boost-python/1.63.0/include -L/usr/local/Cellar/boost-python/1.63.0/lib -I/usr/local/Cellar/boost/1.63.0/include -L/usr/local/Cellar/boost/1.63.0/lib -I/Library/Frameworks/Python.framework/Versions/3.5/include/python3.5m
DYNAMIC_LIB=-shared -undefined dynamic_lookup

test:
	clang $(COMMON) $(EIGEN) CpgFeedbackControl.cpp CPGtest.cpp -o cpg_test