# -*- coding: utf-8 -*-
"""
:author: Austin Stover
:date: September-October 2018

This program institutes the command line interface for the DacManager programs,
as well as for a temperature plate.

Use: Run python cmdUI.py
     -h for man
     On Windows, run cmd.exe as administrator
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
    persisting_vars = pickle.load(open(varFileAbsDir, 'rb'))
    #print(*persisting_vars[:-1])
    cntrl = dm(*persisting_vars[:-1])
    addressDict = persisting_vars[-1]
    return cntrl, addressDict


### DEFINE COMMAND LINE PARSERS

psr = argparse.ArgumentParser(description='Control Voltages on the DACs.')
subpsrs = psr.add_subparsers()

# init command
def init(args):
    print('Settings:','\n\tSlave ID:\t ',args.slaveId,'\n\tPort #:\t\t ',args.port,
          '\n\tBaudrate:\t ',args.baudrate,'\n\tNumber of Boards:',args.numBoards,
          '\n\tAddress txt file:',args.addressFile)
    
    addressDict = {} #Store the address directory here
    with open(args.addressFile) as file: #TODO: Catch file not found error
        for line in file:
            line, _, comment = line.partition('#') #Filter out comments
            if line.strip(): # If a non-blank line
                entries = []
                entries = tuple(line.split())
                addressDict[entries[0]] = tuple(int(i) for i in entries[1:])  #Add or update key-val pair      #TODO: Throw error when only 1 word exists on line i.e. entries[1:] is empty
                #print("Entries:",entries[0])
                
    persisting_vars = (args.slaveId, args.port, args.baudrate, args.numBoards, addressDict) #A tuple of vars to store in between commands
    
    var_file = open(varFileAbsDir, 'wb')
    pickle.dump(persisting_vars,var_file) #Save persisting variables in obj file
    
    #Test connections
    cntrl = dm(*persisting_vars[:-1])
    addressDict = persisting_vars[-1]
    print('Channel List:')
    for key,chan in addressDict.items():
        try:
            #print(*chan)
            print('Alias: ',key,'\tChan #, DAC #, Board #: ',chan,'\tStart Val: ',dm.convertToActualV(cntrl.readV(cntrl.address(*chan))),'V', sep='')
        except KeyError:
            print('Error: DAC channel address',key,'not found')
            exit(1)
            

psr_init = subpsrs.add_parser('init', #aliases=['in']
                                    help='Initialize DAC communications')
psr_init.add_argument('-s','--slaveId', type=int, default=0,
                         help='Choose a different slave.')
psr_init.add_argument('-p','--port', type=str, default=COM_PORT, #TODO: Change default port
                         help='Choose a different port from ' + COM_PORT)
psr_init.add_argument('-n','--numBoards', type=int, default=4,
                         help='Change the number of DAC boards from 4\
                         hooked up to the slave') #TODO: Make sure this is positive, nonzero
psr_init.add_argument('-b','--baudrate', type=int, default=9600,
                         help='Change the baudrate from 9600') #TODO: Make sure this is positive, nonzero
psr_init.add_argument('-a','--addressFile', type=str, default=DAC_DIR_FILE,
                         help='The address directory to specify the channel mapping')
psr_init.set_defaults(func=init)

#powerUp command
def powUp(args):            
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(*addressDict[chan])
            #print(channel)
            #print(addressDict)
            cntrl.powerUp(channel)
            print(chan,': \tPow =',bool(cntrl.getPower(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)

psr_powUp = subpsrs.add_parser('powerUp', aliases=['powUp'],
                                    help='Power up a channel')
psr_powUp.add_argument('chan', type=str, nargs='*',
                          help="Addresses of DAC channels or 'all'")
psr_powUp.set_defaults(func=powUp)

#powerDown command
def powDown(args):
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(channel)
            cntrl.powerDown(channel)
            print(chan,': \tPow =',bool(cntrl.getPower(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)
        
psr_powDown = subpsrs.add_parser('powerDown', aliases=['powDn','powDown'],
                                  help='Power down a channel')
psr_powDown.add_argument('chan', type=str, nargs='*',
                          help="Addresses of DAC channels or 'all'")
psr_powDown.set_defaults(func=powDown)

#getPower command
def getPower(args):
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(channel)
            print(chan,': \tPow =',bool(cntrl.getPower(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)
        
psr_getPow= subpsrs.add_parser('getPower', aliases=['getPow','gtP'],
                                  help='Return whether or not a channel is powered on')
psr_getPow.add_argument('chan', type=str, nargs='*',
                          help="Addresses of DAC channels or 'all'")
psr_getPow.set_defaults(func=getPower)

#getV command
def getV(args):
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(channel)
            print(chan,': \tV =',dm.convertToActualV(cntrl.getV(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)

psr_getV = subpsrs.add_parser('getV', aliases=['gtV'],
                               help='Returns the voltage for the DAC channel')
psr_getV.add_argument('chan', type=str, nargs='*',
                       help="Addresses of DAC channels or 'all'")
psr_getV.set_defaults(func=getV)

#readV command
def readV(args):
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(channel)
            print(chan,': \tV = ',dm.convertToActualV(cntrl.readV(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)

psr_readV = subpsrs.add_parser('readV', aliases=['rdV'],
                               help='Queries the DAC for approximate voltage')
psr_readV.add_argument('chan', type=str, nargs='*',
                       help="Addresses of DAC channels or 'all'")
psr_readV.set_defaults(func=readV)

#updateV command
def updateV(args):
    cntrl, addressDict = init_command()
    if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
        args.chan = list(addressDict.keys())
    for chan in args.chan:
        try:
            channel = cntrl.address(*addressDict[chan])
            #print(channel, args.newV)
            cntrl.updateV(channel, cntrl.convertToRawV(args.newV))
            print(chan,': \tV = ',dm.convertToActualV(cntrl.readV(channel)))
        except KeyError:
            print('Error: DAC channel address for',chan,'not found. See ' +
                  'DacDir.txt or the DAC directory file you specified for ' +
                  'a list of available DAC names.')
            exit(1)

psr_updateV = subpsrs.add_parser('updateV', aliases=['newV'],
                                 help='Updates the voltage on the DAC channel')
psr_updateV.add_argument('newV',type=float,
                         help="New voltage to output")
psr_updateV.add_argument('chan', type=str, nargs='*',
                          help="Addresses of DAC channels or 'all'")
psr_updateV.set_defaults(func=updateV)

### PARSE COMMAND LINE AND EVALUATE
args = psr.parse_args() #Parse the args

if(bool(vars(args))): #Check if command argument supplied
    args.func(args)         #Call whatever function was selected
else:
    raise ValueError('A valid command or option is required to run this script. ' +
                     'Use the option \'-h\' for a list of valid commands and options.')
