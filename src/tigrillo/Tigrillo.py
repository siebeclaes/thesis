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
    setAllResolution(aPins, RESOLUTION)
    setMode(TX_MODE) # IMPORTANT, OTHERWISE NOTHING WILL WORK
    
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
        
# Select read or write mode
def setMode(data):
    pin2.write(data)  
    # print data

# ------------------------------------
# ----------INSTRUCTIONS--------------
# ------------------------------------
# http://support.robotis.com/en/techsupport_eng.htm#product/dynamixel/communication/dxl_packet.htm      # Instruction/status packet
# http://support.robotis.com/en/techsupport_eng.htm#product/dynamixel/communication/dxl_instruction.htm # Kind of Instruction

# ----READ----  
# Gets *rlength* registers starting from regstart (STATUS PACKET (RETURN PACKET))
def getReg(ID, regstart, rlength):  # expects RX_MODE
    waitTillSend = 0
    waitTillRecieve = 0
    # 6 = (Read_data.length = 4) + (Instruction.Read_data.value = 2)
    checksum = 255 - ((6 + ID + regstart + rlength) % 256)
    # Check a few times if the output buffer is empty, if not wait
    # if s.outWaiting() == 0:
        # time.sleep(0.002) # Wait 0.002 seconds between writing and reading
	# Check Sum = !(ID + Length + Instruction + Parameter1 + ... Parameter N) #only lowest bytes
    s.write(chr(0xFF) + chr(0xFF) + chr(ID) + chr(0x04) + chr(SERVO_READ) + chr(regstart) + chr(rlength) + chr(checksum))
    # Tried to solve it elegantly with |while s.outWaiting() != 0|, didn't work, this code was never excecuted
    # Random delay to be determined according to your baudrate it is
    if s.outWaiting() == 0:
        time.sleep(TX_DELAY_TIME)
    setMode(RX_MODE)
    vals = list()
    vals = statusReturn(ID, rlength + 6)
    setMode(TX_MODE)
    return vals
    
# Returns status packet
def statusReturn(ID, NUMBER):  # expects RX_MODE
    wait = 0
    # Important to wait at least one time for respons
    # Check a few times if there is a response
    while s.inWaiting() == 0 and wait < MAX_WAIT_IN:  # Get the number of bytes in the input buffer (try MAX_WAIT_IN-1 times)
        time.sleep(0.001)
        wait = wait + 1
    if s.inWaiting() != NUMBER: # Started too late with reading
        vals = list()
        vals.append(ID)
        vals.append(ERRORTRACK)     
        for i in range(0, NUMBER - 6):
            vals.append(0)
        s.flushInput()
        return vals
    else:
        vals = list()
        statuspacket = s.read(NUMBER)
        vals.append(ord(statuspacket[2]))   # ID
        vals.append(ord(statuspacket[4]))   # Error
        for i in range(5, 5 + NUMBER - 6):  # Parameters + Checksum
            vals.append(ord(statuspacket[i]))
        return vals

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

# Sets STATUS RETURN LEVEL
def setReturn(ID, value):
    # 0 = Never return something except PING command
    # 1 = Only return for READ command
    # 2 = Return for all commands
    return setReg(ID, 16, [value])  # 16 = Satus Return Level 

def action():
    ID = BROADCASTID
    length = 2
    instruction = ACTION
    checksum = 255 - ((ID + length + instruction) % 256)
    # Check Sum = !(ID + Length + Instruction + Parameter1 + ... Parameter N) # Only lowest bytes
    message = chr(0xFF) + chr(0xFF) + chr(ID) + chr(length) + chr(instruction) 
    message = message + chr(checksum)
    s.write(message)
    
def syncWrite(reg, values, howManyAtATime = NUMOFSERVOS): # Default the number of servo's used
    # values should countain ID and data like: ID0, byte1, byte2, ID1, byte3, byte4,...
    ID = BROADCASTID
    length = (((len(values)/NUMOFSERVOS)) * NUMOFSERVOS) + 4    # (L+1)*N + 4 # L = data length(bytes) per servo, N = Number of servo's
    # print length
    instruction = SYNC_WRITE
    dataLength = (len(values) - howManyAtATime)/howManyAtATime
    checksum = 255 - ((ID + length + instruction + reg + dataLength + sum(values)) % 256)
    # Check Sum = !(ID + Length + Instruction + Parameter1 + ... Parameter N) # Only lowest bytes
    message = chr(0xFF) + chr(0xFF) + chr(ID) + chr(length) + chr(instruction) + chr(reg) + chr(dataLength)
    for val in values:
        message = message + chr(val)
    message = message + chr(checksum)
    s.write(message)
    return message
    
def makeSyncWritePacket(values, startID = 0, howManyAtATime = NUMOFSERVOS):
    # Not tested other than with 2 servos
    syncWritePacket = ()
    for id in range(startID, startID + howManyAtATime):
        syncWritePacket += (id,)
        for v in range((len(values)/howManyAtATime)):
            syncWritePacket += (values[v],)
    # for s in range(len(syncWritePacket)):
        # print syncWritePacket[s]
    return syncWritePacket
    
# Sets servo(ID) to given angle (0 to 300 degrees)
def setGoalPos(ID, angle, instruction = SERVO_WRITE):
    #TODO: maybe extra delay
    help = float(float(angle << 10) / 300)  # Convert to range 0 - 1024
    lowbyte = int(help % 256)
    highbyte = int(help) >> 8
    return setReg(ID, 30, ((lowbyte, highbyte)), instruction) # reg30&31 = GoalPosition
    
def getMovingSpeed(ID):
    # (0-1023) 1 unit = 0.111 rpm
    (id, err, lowbyte, highbyte) = getReg(ID, 32, 2)
    return (highbyte << 8) + lowbyte
    
def setMovingSpeed(ID, value, instruction = SERVO_WRITE):
    # (0-1023) 1 unit = 0.111 rpm
    lowbyte = int(value % 256)
    highbyte = int(value) >> 8
    return setReg(ID, 32, ((lowbyte, highbyte))) 
    
def setMovingSpeedPro(ID, value, direction = CCW, instruction = SERVO_WRITE):
    value += direction  # Add 1024 (=CW) to turn CounterWise
    # (0-1023) 1 unit = 0.111 rpm
    lowbyte = int(value % 256)
    highbyte = int(value) >> 8
    return setReg(ID, 32, ((lowbyte, highbyte)), instruction) 
   
def setWheelMode(ID):
    return setReg(ID, 8, ((0, 0)))    #CW and CCW should be 0, CW is standard 0
    
def setJointMode(ID):
    # High = 3, Low = 255, so 1023
    return setReg(ID, 8, ((255, 3)))    #CW and CCW should be different from 0, CW is standard 0
    
def getPosition(ID):
    #TODO: maybe extra delay
	(ids,err,lowbyte,highbyte) = getReg(ID,36,2)    # reg36&37 = PresentPosition
	if err== ERRORTRACK:
		return 200
	else:
		return (highbyte<<8)+lowbyte

def getAngle(ID):
    (ids, err, lowbyte, highbyte) = getReg(ID, 36, 2)  # reg36&37 = PresentPosition
    help = (highbyte << 8) + lowbyte
    angle = (help * 300) / 1024.0  # Shift 10 times to the right = devide by 1023
    angle = round(angle, 1)
    return angle

def convertAngle(angle):
    return float(float(angle << 10) / 300)
    
def convertAngles(angles, beginID = 0, howManyAtATime = NUMOFSERVOS):
    convertedAngles = ()
    for id in range(beginID, howManyAtATime):
        for a in angles: 
            help = float(float(a << 10) / 300)  # Convert to range 0 - 1024
            lowbyte = int(help % 256)
            highbyte = int(help) >> 8
            convertedAngles = convertedAngles + (IDS[id],) + (lowbyte, highbyte)
    return convertedAngles  # reg30&31 = GoalPosition

def setLED(ID, value):
    # 0 = off, 1 = on
    return setReg(ID, 25, [value])
    
def getLED(ID):
    # 0 = off, 1 = on
    (ids, err, byte) = getReg(ID, 25, 1)
    return byte
    
def setReturnDelayTime(ID, usdelay):	#in µs
    # delaytime (µs) = data * 0.2µs
    value = usdelay / 2
    setReg(ID, 5, [value])
    
def setTorqueEnable(ID, value):
    # 0 = off, 1 = on
    return setReg(ID, 24, [value])
    
def getPresentVoltage(ID):
    # voltage = data/10
    (ids, err, byte) = getReg(ID, 42, 1)
    return byte/10.0
    
def getAllVoltages(listIDS):
    voltages = list()
    for id in listIDS:
        voltages.append(id)
        voltages.append(getPresentVoltage(id))
    return voltages
    
def convertDecToBin(decimal):
    return "{0:b}".format(decimal)

def convertBinToDec(binary):
    return int(binary, 2)
    
def selfTest(startID = 1, servos = NUMOFSERVOS):
    print "Executing SELFTEST for %i SERVOS..." % servos
    #turn all LEDS on and then check if the leds are on
    #TODO: for now only tested for 2 servos
    syncWrite(25, makeSyncWritePacket(((1,1)),startID, servos), servos)
    time.sleep(1) 
    numOfSuccessFullServos = 0
    for s in range(startID, servos + 1):
        numOfSuccessFullServos += getLED(s)
        time.sleep(0.001)
    if numOfSuccessFullServos == servos:
        print "SELF TEST SUCCEEDED"
    else:
        print "SELF TEST FAILED"
    time.sleep(1) 
    syncWrite(25, makeSyncWritePacket(((0,0)),1,2), 2)
    
def selfTestPro(listIDS):
    print "Executing SELFTEST for %i SERVOS..." % len(listIDS)
    #turn all LEDS on and then check if the leds are on
    for id in listIDS:
        setLED(id,1)
    time.sleep(1)
    numOfSuccessFullServos = 0
    for id in listIDS:
        numOfSuccessFullServos += getLED(id)
        time.sleep(0.001)
    if numOfSuccessFullServos == len(listIDS):
        print "SELF TEST SUCCEEDED"
    else:
        print "SELF TEST FAILED"
        print "Only %i servo(s) responded" % numOfSuccessFullServos
    time.sleep(1)
    for id in listIDS:
        setLED(id,0)
        
def doForAll(method, *args):
    # Special thanks to:
    # http://stackoverflow.com/questions/803616/passing-functions-with-arguments-to-another-function-in-python
    for id in listIDS:
        method(id, *args)
        time.sleep(0.1)
    
def doForFront(method, *args):
    for id in allIDS[:2]:
        method(id, *args)
        # time.sleep(0.0000001)
        
def doForFrontAction(method, *args):
    for id in allIDS[:2]:
        method(id, *args)
    if args[-1] == REG_WRITE:   # Check if last element is REG_WRITE
        action()

def setAngleForFrontAction(angle, instruction = SERVO_WRITE):  # Angle is relative to CENTERANGLE
    setGoalPos(1, CENTERANGLE - angle, instruction)
    setGoalPos(2, CENTERANGLE + angle, instruction)
    if instruction == REG_WRITE:
        action() 
        
def doForBack(method, *args):
    for id in allIDS[2:4]:
        method(id, *args)
        # time.sleep(0.0000001)
        
def doForBackAction(method, *args):
    for id in allIDS[2:4]:
        method(id, *args)  
    if args[-1] == REG_WRITE:   # Check if last element is REG_WRITE
        action()
        
def setAngleForBackAction(angle, instruction = SERVO_WRITE):  # Angle is relative to CENTERANGLE
    setGoalPos(3, CENTERANGLE - angle, instruction)
    setGoalPos(4, CENTERANGLE + angle, instruction)
    if instruction == REG_WRITE:
        action() 
     
def setSpeedForBack(method, speed):
    setMovingSpeedPro(allIDS[2], speed, CW)
    setMovingSpeedPro(allIDS[3], speed, CCW)
    time.sleep(0.001)
     
def setSpeedForBackAction(method, speed, instruction = SERVO_WRITE):
    setMovingSpeedPro(allIDS[2], speed, CW, instruction)
    setMovingSpeedPro(allIDS[3], speed, CCW, instruction)
    if instruction == REG_WRITE:
        action()
    time.sleep(0.0001)

def centerAllServos():
    print "Centering all servos..."
    doForAll(setJointMode)
    setGoalPos(1, int(CENTERANGLE))
    setGoalPos(2, int(CENTERANGLE))
    setGoalPos(3, int(CENTERANGLE))
    setGoalPos(4, int(CENTERANGLE))
    print "Centering servos: Done"
    
def centerAllServosWithOffset():
    print "Centering all servos..."
    doForAll(setJointMode)
    setGoalPos(1,int(CENTERANGLE - CNTROFFFLC - CENTEROFFSETFRUN))
    setGoalPos(2,int(CENTERANGLE + CNTROFFFRC + CENTEROFFSETFRUN))
    setGoalPos(3,int(CENTERANGLE - CNTROFFBLC - CENTEROFFSETBRUN))
    setGoalPos(4,int(CENTERANGLE + CNTROFFBRC + CENTEROFFSETBRUN))
    print "Centering servos: Done"

def splitInTwoBytes(twoBytes):
    lowbyte = int(twoBytes % 256)
    highbyte = int(twoBytes) >> 8
    return ((lowbyte, highbyte))
    
def makeDoublePackage(position, speed):
    return (splitInTwoBytes(position) + splitInTwoBytes(speed))
     
def getUp():
    print "Standing up..."
    doForAll(setJointMode)
    # FIRST BACK LEGS, THEN FRONT LEGS!!!
    # Set goal position and moving speed at once
    setReg(3, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE - CNTROFFBLC - CENTEROFFSETBU)),500)))
    time.sleep(0.001)
    setReg(4, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE + CNTROFFBRC + CENTEROFFSETBU)),500)))
    time.sleep(0.1)
    setReg(1, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE - CNTROFFFLC - CENTEROFFSETFU)),500)))
    time.sleep(0.001)
    setReg(2, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE + CNTROFFFRC + CENTEROFFSETFU)),500)))
    time.sleep(0.001) 
    print "Standing up: Done"
    
def getDown():
    print "Laying down..."
    doForAll(setJointMode)
    setReg(3, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE - 70)),100)))
    time.sleep(0.001)
    setReg(4, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE + 70)),100)))
    time.sleep(0.5)
    setReg(1, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE - 100)),100)))
    time.sleep(0.001)
    setReg(2, 30,(makeDoublePackage(convertAngle(int(CENTERANGLE + 100)),100)))
    time.sleep(0.001) 
    print "I'm taking a nap :)"
    
def generate(delay = 0):
    T = WAITTIME + time.time() - OFFSETTIME
    # return calculatePositionSine(T, delay) 
    return calculateLinApprox(T, delay)
    
def generatePro(delay = 0):
    T = WAITTIME + time.time() - OFFSETTIME
    if SINEWAVE:
        FL = calculatePositionSine(T) #delay removed
        FR = calculatePositionSine(T)
        BL = calculatePositionSine(T, delay)
        BR = calculatePositionSine(T, delay)
    else:
        FL = calculateLinApproxPro(T, xListF, yListF)
        FR = calculateLinApproxPro(T, xListF, yListF)
        BL = calculateLinApproxPro(T, xListB, yListB, delay)
        BR = calculateLinApproxPro(T, xListB, yListB, delay)
    updateServos(FL,FR,BL,BR)

def generateCPG(actions, delay = 0):
    T = WAITTIME + time.time() - OFFSETTIME
    print T
    # if T > 5:
    #     a = [20, 20, 20, 20]
    # else:
    #     a = [0, 0, 0, 0]
    a = actions[int(T*100)]
    # print a
    updateServos(a[0], a[1], a[2], a[3])

    
def calculatePositionSine(T, delay = 0):
    # T = time
    # General sine function
    return aSin * math.sin(bSin*((T + delay) - cSin))

def calculatePositionSpline(time, delay = 0):
    return "not implemented"
    
def calculateLinApprox(time, delay = 0):
    time = (time + delay) % PERIOD # Recalculate current time to one period
    time = time/PERIOD #Devided by a period, the interval is now [0,1]
    return aSin * np.interp(time, xListF, yListF)
    
def calculateLinApproxPro(time, xList = xListF, yList = yListF, delay = 0):
    time = (time + delay) % PERIOD # Recalculate current time to one period
    time = time/PERIOD #Devided by a period, the interval is now [0,1]
    return aSin * np.interp(time, xList, yList)

def setAllResolution(aPinArray, res = RESOLUTION):
    for a in range(len(aPins)):
        aPins[a].setBit(res) 

def getVoltage(aPin):
    val = aPin.readFloat()
    val = val * REFVOLTAGE
    return val

@timeout(0.020)    
def distanceUS():
    tZero = time.time()
    # reading sensor in Python takes about 6 ms (US = Utrasonic Sensor)
    # http://stackoverflow.com/questions/32300000/galileo-and-ultrasonic-error-when-distance-less-than-4cm
    # http://playground.arduino.cc/Main/UltrasonicSensor
    
    trig.write(0)
    time.sleep(0.000004) # in Arduino 2 microseconds, double this value to be sure

    trig.write(1)
    time.sleep(0.00001) # in Arduino 5 microseconds, double this value to be sure
    trig.write(0)
    
    sig = None
    nosig = None
    etUS = None
    
    while echo.read() == 0:
            nosig = time.time()

    while echo.read() == 1:
            sig = time.time()

    if sig == None or nosig == None:
        return 0
               
    # et = Elapsed Time
    etUS = sig - nosig

    distance =  etUS * 17150
                
    return distance

def getSensorValues(start, howmanysensors, senstype):
    aVal[0] = time.time() - OFFSETTIME
    for i in range(start, start + howmanysensors):
        try:
            if senstype == "current":
                aVal[i+1] = convertToAmpere(getVoltage(aPins[i]))
                # aVal[i+1] = aPins[i].read()
            elif senstype == "distance":
                aVal[i] = convertToDistance(getVoltage(aPins[i]))
        except Exception, e:
            print e
            print ("Are you sure you have an ADC?")

def convertToAmpere(volt):
    return (volt - SENSOFFSET)/SENSITIVITY

def convertToDistance(volt):
    if (volt > UPPERVOLTBOUNDARY):
        volt = UPPERVOLTBOUNDARY
    elif (volt < LOWERVOLTBOUNDARY):
        volt = LOWERVOLTBOUNDARY
    return (MULTIPLIER * math.pow(volt, EXPONENT))

def printSensData():
    for sensval in aVal:
        print sensval
        
def logSensData():
    wCSV.writerow(aVal)
        
def testGaitSpline(SAME = True, GAITTESTDELAY = 10.0):
    yMinF = yListF.min()
    yMaxF = yListF.max()
    yMinB = yListB.min()
    yMaxB = yListB.max()
    # if SAME == True:
        # yMinB = yMinF
        # yMaxB = yMaxF
    # else:
        # yMinB = yListB.min()
        # yMaxB = yListB.max()
    while True:
        print "yMin"
        updateServos(aSin*yMinF,aSin*yMinF,aSin*yMinB,aSin*yMinB)
        time.sleep(GAITTESTDELAY)
        print "yMax"
        updateServos(aSin*yMaxF,aSin*yMaxF,aSin*yMaxB,aSin*yMaxB)
        time.sleep(GAITTESTDELAY)
        print "Neutral"
        updateServos(0,0,0,0)
        time.sleep(GAITTESTDELAY)
        
def testGaitSine(SAME = True, GAITTESTDELAY = 10.0):
    while True:
        print "yMin"
        updateServos(aSin,aSin,aSin,aSin)
        time.sleep(GAITTESTDELAY)
        print "yMax"
        updateServos(-aSin,-aSin,-aSin,-aSin)
        time.sleep(GAITTESTDELAY)
        print "Neutral"
        updateServos(0,0,0,0)
        time.sleep(GAITTESTDELAY)
        
def readSensors():
    sensData = list()
    sensData.append(getVoltage(0))
    sensData.append(getVoltage(1))
    return sensData
   
def updateServos(FL, FR, BL, BR):
    setGoalPos(1,int(CENTERANGLE - CNTROFFFLC - CENTEROFFSETFRUN - FL), REG_WRITE)
    setGoalPos(2,int(CENTERANGLE + CNTROFFFRC + CENTEROFFSETFRUN + FR), REG_WRITE)
    setGoalPos(3,int(CENTERANGLE - CNTROFFBLC - CENTEROFFSETBRUN - BL), REG_WRITE)
    setGoalPos(4,int(CENTERANGLE + CNTROFFBRC + CENTEROFFSETBRUN + BR), REG_WRITE)
    action()
    aVal[4] = FL
    aVal[5] = BL

def loadControlSignalFromFile(filename):
    import pickle
    with open(filename, 'rb') as f:
        actions = pickle.load(f)
        return actions

def loadCpgParamsFromFile(filename):
    import pickle
    with open(filename, 'rb') as f:
        params = pickle.load(f)
        print params
        return loadCpgParams(params)


def loadCpgParams(x):
    from CpgControl import CPGControl

    mu = [x[0], x[1], x[2], x[3]]
    o = [x[4], x[4], x[5], x[5]]
    omega = [x[6], x[6], x[7], x[7]]
    d = [x[8], x[8], x[9], x[9]]
    coupling = [[0, x[10], x[11], x[13]], [x[10], 0, x[12], x[14]], [x[11], x[12], 0, x[15]], [x[13], x[14], x[15], 0]]
    phase_offset = x[16]

    cpg = CPGControl(mu, o, omega, d, coupling, phase_offset)
    return cpg

actions = loadControlSignalFromFile('2_variations_control_signal.pickle')

print 'Loaded actions, start running'
    
init()

if CENTERPOSITION:
    # getUp()
    centerAllServosWithOffset()
    # centerAllServos()
    # pass

if SELFTEST:
    selfTestPro(listIDS)

if TESTGAIT:
    doForAll(setJointMode)
    doForAll(setMovingSpeed, 100) # Max speed
    time.sleep(0.2)
    testGaitSine(True, 15.0)
    
if LOGGING:
    fileDir = "".join(("LogFiles/", "log", str(CONFIGNo).zfill(4), ".csv")) # Add 4 leading zero's
    # filePath = os.path.relpath("LogFiles/templog.csv")
    fLog = open(fileDir, 'wb') # TODO: was 'a' from append, maybe b from binary?
    wCSV = csv.writer(fLog)
   
    
OFFSETTIME = time.time()
t0 = 0.0
timeleftover = 0.0

print "Start logging..."
   
# print "Voltages of servos: ", getAllVoltages(listIDS)


# setReturnDelayTime(1, 20)
# setReg(testid, 5, ((100,)))  # set Return Delay Time to 100*0.2=20µs = 0.020ms
time.sleep(0.0000001)
pos = 0
idnr = 0


# actions = []

try:

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
            if LOGGING:
                print "Logging..."
                getSensorValues(0,2,"current")
                try:
                    # print distanceUS()
                    aVal[3] = distanceUS()
                except Exception, e:
                    # print 'time out!'
                    continue
                logSensData()
            print (time.time() - t0)
            tlf = CONTROLLOOPDELAY - (time.time() - t0)
            if tlf > 0:
                time.sleep(tlf) 
except:
    for i in IDS:
        setTorqueEnable(i, 0)

        
print "Current sensing..."
getSensorValues(0,2,"current")
printSensData()

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