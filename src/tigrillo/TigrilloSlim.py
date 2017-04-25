#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Otherwise it gives an error for non-ASCII characters in comments

#-------------------------------------------------------------------
# Author: Peter Timmerman (2014-2015)
# Contact: peter *dot* timmerman *at*  gmail *dot* com
#
# Modified by: Brecht Willems (2015-2016)
# Contact: brecht *dot* willems *dot* bw *at* gmail *dot* com
#-------------------------------------------------------------------

import serial   # https://pyserial.readthedocs.org/en/latest/pyserial_api.html
import time
import math
import signal   # Set handlers for asynchronous events
import sys
import os
import csv
import re
import glob
import numpy as np
# eglibc needed: https://software.intel.com/en-us/iot/hardware/galileo/downloads
import mraa 	# Intel IOT library for Intel Galileo: https://github.com/intel-iot-devkit/mraa
from timeout import timeout 

# ---- GENERAL PARAMETERS -----
SELFTEST        = False
CENTERPOSITION  = True
NOTORQUEONEND   = True
READVOLTAGES    = False
TESTGAIT        = False
SAME            = False
SINEWAVE        = False
LOGGING         = True
VERBOSE         = False # Set this true if you want extra information printed to console
VERBOSE2        = False
CONTROLLOOPDELAY= 0.020
CONFIGNo = 0

# Only start running when "python *filename* run"; otherwise just center servos
if len(sys.argv) >= 2 and str(sys.argv[1]) == "run":
    RUN   = True
    # print sys.argv, len(sys.argv)
    if len(sys.argv) >= 3 and sys.argv[2].isdigit() == True: # 0042 for example
        CONFIGNo = int(sys.argv[2])
    else:
        logfile_path = "LogFiles/*.csv"
        file_list = glob.glob(logfile_path)
        last_file_path =  sorted(file_list)[-1]
        last_file_name = os.path.basename(last_file_path)

        #http://stackoverflow.com/questions/430079/how-to-split-strings-into-text-and-number
        match = re.match(r"([a-z]+)([0-9]+)", last_file_name, re.I)
        if match:
            items = match.groups()
            last_file_number =  int(items[1])
            # print last_file_number

        CONFIGNo = last_file_number + 1
    print "Config No: %s" % (CONFIGNo)
else:
    RUN   = False
    print "To run type: python " + os.path.basename(__file__) + " run"

from allData import lines, freq
# from allData import lines
xyValF, xyValB = lines[CONFIGNo - 1]
# xyValF, xyValB = lines[0] #always choose the first one, (for Particle Swarm)
if VERBOSE2:
    print xyValF
    print xyValB
    print freq[CONFIGNo - 1]
    
if SAME == True:
    xyValB = list(xyValF) # Copy list in another list

# This is the linear approximation of a spline
(xListF,yListF) = zip(*xyValF)
xListF = np.array(xListF)
yListF = np.array(yListF)
(xListB,yListB) = zip(*xyValB)
xListB = np.array(xListB)
yListB = np.array(yListB)

# ---- CURVE PARAMETERS ----
# FREQUENCY   = 2.2
FREQUENCY   = freq[CONFIGNo - 1]
PERIOD      = (1.0/FREQUENCY)
# PHASE       = (PERIOD/2.0) #* 1.5
DELAY       = 0.0
# DELAY     = 0.01
STEP        = 100
# DELAY     = PERIOD / 50
# NUMOFSAMPLES = int(PERIOD/DELAY)

aSin = 30.0     # Vertical Scaling Factor # Maximum distance from equilibrium
bSin = 20.0     # Horizontal Scaling Factor
cSin = 0.0      # Phase Move
dSin = 150.0    # Vertical Move # Centerpoint of the 300 degrees of the servo

# Calculate bSin from the frequency # Easier control
# Overwrites previous values of bSin
bSin =  (2 * math.pi) / PERIOD
# print bSin

# http://support.robotis.com/en/techsupport_eng.htm#product/dynamixel/communication/dxl_packet.htm
# ----------------- INSTRUCTIONS -----------------
# NAME 			= Value		#No. of Parameters
# ------------------------------------------
# PING		 	= 0x01 		# 0
SERVO_READ	 	= 0x02  	# 2+
SERVO_WRITE	 	= 0x03  	# 2+
REG_WRITE		= 0x04		# 2+
ACTION 		    = 0x05		# 0
# RESET 		= 0x06		# 0
SYNC_WRITE 	    = 0x83		# 4+

RX_MODE         = 0         # Receive eXtention
TX_MODE         = 1         # Transmit eXtention
MAX_WAIT_IN     = 3         # Max tries when receiving
MAX_WAIT_OUT    = 8         # Max tries when sending
NUMOFSERVOS     = 4         # Nr of servos
ENDCHAR         = '$'       # Used in communication

POSFB           = False     # Position FeedBack
RUNNING         = False
OFFSETTIME      = 0.0
WAITTIME        = 0.0

BROADCASTID     = 0xFE      # 254
ERRORTRACK      = 42        # Answer to the Ultimate Question of Life, the Universe, and Everything

CCW             = 0         # CounterClockWise 
CW              = 1024      # ClockWise

CENTERANGLE     = 150.0
#Discs on legs are not glued in the same position, correcting parameters...
CNTROFFFLC      = -0.0      #(F)ront (L)eft
CNTROFFFRC      = -0.0      #(F)ront (R)ight
CNTROFFBLC      = -0.0      #(B)ack (L)eft
CNTROFFBRC      = -0.0      #(B)ack (R)ight
# Offset needed to stand up
CENTEROFFSETFU  = 15.0     #(F)ront for upright #15.0
CENTEROFFSETBU  = -30.0      #(B)ack #-30.0
# Offset center of sine in running mode
if SINEWAVE:
    CENTEROFFSETFRUN= -0.0     #(F)ront # was -0.0
    CENTEROFFSETBRUN= -20.0     #(B)ack  # was -20.0
else:
    CENTEROFFSETFRUN= 25.0      #(F)ront # was -10.0
    CENTEROFFSETBRUN= 0     #(B)ack  # was -30.0

IDS             = ((1, 2, 3, 4)) #Left Front (LF), Right Front (RF), Hind Left (HL), Hind Right (HR)
allIDS          = [1,2,3,4]
listIDS         = [1,2,3,4] # Used for testing when not all servos are connected
positionList    = list()
# print "IDS :", IDS

# ---- SENSOR/GPIO SETTINGS ----
RESOLUTION      = 12
NUMOFSENSORS    = 2
REFVOLTAGE      = 5.0   # Can be changed to 3.3V if needed
STARTADCPIN     = 0

# Parameters for GP2Y0A41SK0F
# https://www.pololu.com/product/2464
MULTIPLIER      = 12.381
EXPONENT        = -1.096
UPVOLTBOUNDARY  = 3
LOWVOLTBOUNDARY = 0.4

# Parameters for Allegro current sensor ACS713
SENSOFFSET      = 0.5   # DC-offset sensor
SENSITIVITY     = 0.185 # Sensitivity of current sensor in V/A

# Setting for Ultrasonic Sensor HC-SR04
trig = mraa.Gpio(3)
echo = mraa.Gpio(4)

trig.dir(mraa.DIR_OUT)
echo.dir(mraa.DIR_IN)

aVal = [None] * (NUMOFSENSORS+2+2) #time, distance, curr1, curr2, pos1, pos2

aPins = list()
for i in range(STARTADCPIN, STARTADCPIN + NUMOFSENSORS):
    aPins.append(mraa.Aio(i))

# ---- LIBRARY INITIALISATION ----
s = serial.Serial()

# print "Numpy version: ", np.version.version
# print "mraa version : ", mraa.getVersion()
# print "Platform name: ", mraa.getPlatformName()

pin2 = mraa.Gpio(2) 

TX_DELAY_TIME = 0.000001 # CHANGE THIS ACCORDING TO YOUR BAUDRATE #TRAIL_AND_ERROR or use an oscilloscope

# -- Notes --
# This code is focused on writing, consistent valid readings without manual tweaking,
#  when a different baudrate is used, have to be implemented (switching direction bit)
# Errors in response packet are not thoroughly implemented (error message, checksum, id check)
# Not speed optimized between read/write

def init():
    mraa.Uart(0)    # Use mraa to initialize the serial port, then use default pyserial library
    # Open serial communication on pin 0(RX) and 1(TX)
    s.baudrate = 115200
    s.port = "/dev/ttyS0"
    s.timeout = 0
    s.open()
    # print s
    
    signal.signal(signal.SIGINT, signal_handler)
    print "Press Ctrl+C to stop the motors and the program"

    # Sets digital pin2(=Direction) to output
    pin2.dir(mraa.DIR_OUT)
    setAllResolution(aPins, RESOLUTION) # CurrentSensing pins setup
    setMode(TX_MODE) # IMPORTANT, OTHERWISE NOTHING WILL WORK

# Select read or write mode
def setMode(data):
    pin2.write(data)  
    
def signal_handler(signal, frame):
    # Interrupt handler
    # http://stackoverflow.com/questions/4205317/capture-keyboardinterrupt-in-python-without-try-except
    print "You pressed Ctrl+C!"
    print "Executing clean exit..."
    stopAllWheels();
    if LOGGING:
        fLog.close()
    print "-- Test %s has ended --" % (CONFIGNo)
    sys.exit(0)
    
def stopAllWheels():
    # Active stop all motors, otherwise servos in wheel mode keep spinning
    print "Stopping motors..."
    if NOTORQUEONEND:
        print "Disabling torque of motors, (to save power)..."
    for i in IDS:
        setMovingSpeed(i,0)
        if NOTORQUEONEND:
            setTorqueEnable(i, 0)

# ----WRITE----
# Sets given values starting in addres of reg (INSTRUCTION PACKET)
def setReg(ID, reg, values, instruction = SERVO_WRITE): # default SERVO_WRITE instruction
    # Use REG_WRITE for buffered instruction excecuted with action commmand
    length = 3 + len(values)
    checksum = 255 - ((ID + length + instruction + reg + sum(values)) % 256)
    # Check Sum = !(ID + Length + Instruction + Parameter1 + ... Parameter N) # Only lowest bytes
    message = chr(0xFF) + chr(0xFF) + chr(ID) + chr(length) + chr(instruction) + chr(reg)
    for val in values:
        message = message + chr(val)
    message = message + chr(checksum)
    s.write(message)

# Sets servo(ID) to given angle (0 to 300 degrees)
def setGoalPos(ID, angle, instruction = SERVO_WRITE):
    #TODO: maybe extra delay
    help = float(float(angle << 10) / 300)  # Convert to range 0 - 1024
    lowbyte = int(help % 256)
    highbyte = int(help) >> 8
    return setReg(ID, 30, ((lowbyte, highbyte)), instruction) # reg30&31 = GoalPosition

def setJointMode(ID):
    # High = 3, Low = 255, so 1023
    return setReg(ID, 8, ((255, 3)))    #CW and CCW should be different from 0, CW is standard 0


def centerAllServosWithOffset():
    print "Centering all servos..."
    doForAll(setJointMode)
    setGoalPos(1,int(CENTERANGLE - CNTROFFFLC - CENTEROFFSETFRUN))
    setGoalPos(2,int(CENTERANGLE + CNTROFFFRC + CENTEROFFSETFRUN))
    setGoalPos(3,int(CENTERANGLE - CNTROFFBLC - CENTEROFFSETBRUN))
    setGoalPos(4,int(CENTERANGLE + CNTROFFBRC + CENTEROFFSETBRUN))
    print "Centering servos: Done"

def setMovingSpeed(ID, value, instruction = SERVO_WRITE):
    # (0-1023) 1 unit = 0.111 rpm
    lowbyte = int(value % 256)
    highbyte = int(value) >> 8
    return setReg(ID, 32, ((lowbyte, highbyte)))


def updateServos(FL, FR, BL, BR):
    setGoalPos(1,int(CENTERANGLE - CNTROFFFLC - CENTEROFFSETFRUN - FL), REG_WRITE)
    setGoalPos(2,int(CENTERANGLE + CNTROFFFRC + CENTEROFFSETFRUN + FR), REG_WRITE)
    setGoalPos(3,int(CENTERANGLE - CNTROFFBLC - CENTEROFFSETBRUN - BL), REG_WRITE)
    setGoalPos(4,int(CENTERANGLE + CNTROFFBRC + CENTEROFFSETBRUN + BR), REG_WRITE)
    action()
    aVal[4] = FL
    aVal[5] = BL


def action():
    ID = BROADCASTID
    length = 2
    instruction = ACTION
    checksum = 255 - ((ID + length + instruction) % 256)
    # Check Sum = !(ID + Length + Instruction + Parameter1 + ... Parameter N) # Only lowest bytes
    message = chr(0xFF) + chr(0xFF) + chr(ID) + chr(length) + chr(instruction) 
    message = message + chr(checksum)
    s.write(message)

init()

if CENTERPOSITION:
    # getUp()
    centerAllServosWithOffset()
    # centerAllServos()
    # pass

OFFSETTIME = time.time()
t0 = 0.0
timeleftover = 0.0

time.sleep(0.0000001)
pos = 0
idnr = 0


# actions = []

if RUN:
    doForAll(setJointMode)
    doForAll(setMovingSpeed, 0) # Max speed
    # setSpeedForBackAction(setMovingSpeedPro, 700, REG_WRITE)

    while (1):
        # break
        # Calculate elapsed time
        t0 = time.time()
        # generatePro(PHASE)        
        generateCPG(actions)
        
        print (time.time() - t0)
        tlf = CONTROLLOOPDELAY - (time.time() - t0)
        if tlf > 0:
            time.sleep(tlf) 

time.sleep(30)    
   
getDown()

time.sleep(2)

for i in IDS:
    setTorqueEnable(i, 0)

while True:
    time.sleep(5)
    print "Angles"
    for i in allIDS:
        print getAngle(i) - CENTERANGLE
        time.sleep(0.001)
