# -*- coding: utf-8 -*-
"""
:author: Austin Stover
:date: September-October 2018

This program institutes the command line interface for the DacManager programs,
as well as for a temperature plate.

Use: Run python cmdUI.py
     -h for man
     On Windows, run cmd.exe as administrator

     TODO: Add "all" to cmd line addresses
"""

from DacMaster import DacMaster as dm
import argparse
import pickle
import os

### DEFAULTS

COM_PORT = '/dev/ttyUSB0' # Winows com port: 'COM4'  Raspbian Com port: '/dev/ttyUSB0'
DAC_DIR_FILE = 'DacDir.txt' #Dac Directory File

### HANDLE PERSISTING VARIABLES

VAR_FILE_DIR = ''
VAR_FILE_NAME = 'cmd_UI_vars.obj' #Should have extension '.obj' in it

varFileAbsDir = os.path.join(os.path.dirname(__file__),VAR_FILE_DIR,VAR_FILE_NAME) #Absolute directory

def init_command(): #Unpack vars from file and reinitialize cntrl object
    persisting_vars = pickle.load(open(varFileAbsDir, 'rb')) #open() only works with admin priveleges
    print(*persisting_vars[:-1])
    cntrl = dm(*persisting_vars[:-1])
    addressDict = persisting_vars[-1]
    return cntrl, addressDict


### DEFINE COMMAND LINE PARSERS

psr = argparse.ArgumentParser(description='Control Voltages on the DACs; \
                                 Measure temp; Control peltier cooler.')
subpsrs = psr.add_subparsers()

# init command
def init(args):
    print(args)
    print(args.slaveId, args.port, args.baudrate, args.numBoards, args.addressFile)
    
    addressDict = {} #Store the address directory here
    with open(args.addressFile) as file: #TODO: Catch file not found error
        for line in file:
            line, _, comment = line.partition('#') #Filter out comments
            if line.strip(): # If a non-blank line
                entries = []
                entries = tuple(line.split())
                addressDict[entries[0]] = tuple(int(i) for i in entries[1:])  #Add or update key-val pair      #TODO: Throw error when only 1 word exists on line i.e. entries[1:] is empty
    
    print(addressDict)
    
    persisting_vars = (args.slaveId, args.port, args.baudrate, args.numBoards, addressDict) #A tuple of vars to store in between commands
    
    var_file = open(varFileAbsDir, 'wb')
    pickle.dump(persisting_vars,var_file) #Save persisting variables in obj file
            

psr_init = subpsrs.add_parser('init', #aliases=['in']
                                    help='Initialize DAC communications')
psr_init.add_argument('-s','--slaveId', type=int, default=0,
                         help='Choose a different slave.')
psr_init.add_argument('-p','--port', type=str, default=COM_PORT, #TODO: Change default port
                         help='Choose a different port from ' + COM_PORT)
psr_init.add_argument('-n','--numBoards', type=int, default=1,
                         help='Change the number of DAC boards from 1\
                         hooked up to the slave') #TODO: Make sure this is positive, nonzero
psr_init.add_argument('-b','--baudrate', type=int, default=9600,
                         help='Change the baudrate from 9600') #TODO: Make sure this is positive, nonzero
psr_init.add_argument('-a','--addressFile', type=str, default=DAC_DIR_FILE,
                         help='The address directory to specify the channel mapping')
psr_init.set_defaults(func=init)

#powerUp command
def powUp(args):
    cntrl, addressDict = init_command()
    try:
        channel = cntrl.address(*addressDict[args.chan])
        print(*addressDict[args.chan])
        print(channel)
        print(addressDict)
        cntrl.powerUp(channel)
    except KeyError:
        print('Error: DAC channel address not found')
        exit(1)

psr_powUp = subpsrs.add_parser('powerUp', aliases=['powUp'],
                                    help='Power up a channel')
psr_powUp.add_argument('chan', type=str, 
                          help="Address of DAC channel")
psr_powUp.set_defaults(func=powUp)

#powerDown command
def powDown(args):
    cntrl, addressDict = init_command()
    try:
        channel = cntrl.address(*addressDict[args.chan])
        print(channel)
        cntrl.powerDown(channel)
    except KeyError:
        print('Error: DAC channel address not found. See DacDir.txt or the ' +
              'DAC directory file you specified for a list of available DAC ' +
              'names.')
        exit(1)
        
psr_powDown = subpsrs.add_parser('powerDown', aliases=['powDn','powDown'],
                                  help='Power down a channel')
psr_powDown.add_argument('chan', type=str, 
                          help="Address of DAC channel")
psr_powDown.set_defaults(func=powDown)

#getV command
def getV(args):
    cntrl, addressDict = init_command()
    try:
        channel = cntrl.address(*addressDict[args.chan])
        print(channel)
        cntrl.getV(channel)
    except KeyError:
        print('Error: DAC channel address not found')
        exit(1)

psr_getV = subpsrs.add_parser('getV', aliases=['gtV'],
                               help='Returns the voltage for the DAC channel')
psr_getV.add_argument('chan', type=str, 
                       help="Address of DAC channel")
psr_getV.set_defaults(func=getV)

#updateV command
def updateV(args):
    cntrl, addressDict = init_command()
    try:
        channel = cntrl.address(*addressDict[args.chan])
        print(channel, args.newV)
        cntrl.updateV(channel, cntrl.convertToRawV(args.newV))
    except KeyError:
        print('Error: DAC channel address not found')
        exit(1)

psr_updateV = subpsrs.add_parser('updateV', aliases=['newV'],
                                 help='Updates the voltage on the DAC channel')
psr_updateV.add_argument('chan', type=str, 
                          help="Address of DAC channel")
psr_updateV.add_argument('newV',type=float,
                         help="New voltage to output")
psr_updateV.set_defaults(func=updateV)

### PARSE COMMAND LINE AND EVALUATE
args = psr.parse_args() #Parse the args

if(bool(vars(args))): #Check if command argument supplied
    args.func(args)         #Call whatever function was selected
else:
    raise ValueError('A valid command or option is required to run this script. ' +
                     'Use the option \'-h\' for a list of valid commands and options.')