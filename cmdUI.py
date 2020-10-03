# -*- coding: utf-8 -*-
"""
This program institutes the command line interface for the DacManager programs.
It lets you control DACs and temperature sensor through a friendly interface!

To use: On your preferred terminal, run
    "python cmdUI.py [command] [option(s)] [args]"
    
Use the option "--help" or "-h" to access the documentation

..  moduleauthor:: Austin Stover <stover.a@wustl.edu>
    :date: Sept 2018-Sept 2020

Copyright (C) 2020  Austin Stover

This file is part of APTDacManager.

    APTDacManager is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    APTDacManager is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with APTDacManager.  If not, see <https://www.gnu.org/licenses/>.
"""

from DacMaster import DacMaster as dm
import argparse
import pickle
import os
import time

### DEFAULTS

COM_PORT        = '/dev/ttyUSB0'    # Default serial port. Typical Windows com port: 'COM13'  Typical Raspbian Com port: '/dev/ttyUSB0'
DAC_DIR_FILE    = 'DacDir.txt'      #DAC Directory default filename.
TEMP_DIR_FILE   = 'TempDir.txt'     #Temperature controller directory default filename.
NUM_BOARDS      = 4                 #The default number of DAC boards connected to the Arduino. Should be the same as NUM_BOARDS in the Arduino code.
SLAVE_ID        = 1                 #The default slave ID to use. Must be the same as SLAVE_ID in the Arduino code.
BAUD_RATE       = 9600              #The default serial baud rate for communication with the Arduino.
TIMEOUT         = 0.3               #The modbus serial timeout. Waits no longer for a modbus message response from the Arduino.

### HANDLE PERSISTING VARIABLES

VAR_FILE_DIR = ''
VAR_FILE_NAME = 'cmd_UI_vars.obj' #Should have extension '.obj' in it

varFileAbsDir = os.path.join(os.path.dirname(__file__),VAR_FILE_DIR,VAR_FILE_NAME) #Absolute directory

def init_command(): #Unpack vars from file and reinitialize cntrl object
    persisting_vars = pickle.load(open(varFileAbsDir, 'rb'))
    #print(*persisting_vars[:-1])
    cntrl = dm(*persisting_vars[:-3])
    addressDict = persisting_vars[-3]
    tempDict    = persisting_vars[-2]
    iv_tempDict = persisting_vars[-1]
    return cntrl, addressDict, tempDict, iv_tempDict


### DEFINE COMMAND LINE PARSERS
def return_parser():
    psr = argparse.ArgumentParser(description='Control Voltages on the DACs ' +
                                  'and read temperature sensors with this ' +
                                  'interface. Make sure cmdUI.py is on your ' +
                                  'PythonPath before use.')
    subpsrs = psr.add_subparsers()
    
    # init command
    def init(args):
        print('Settings:','\n\tSlave ID:\t ',args.slaveId,'\n\tPort #:\t\t ',args.port,
              '\n\tBaudrate:\t ',args.baudrate,'\n\tNumber of Boards:',args.numBoards,
              '\n\tAddress txt file:',args.addressFile,
              '\n\tTemperature Serial Code txt file',args.tempFile)
        
        addressDict = {} #Store the address directory here
        with open(args.addressFile) as file:
            for line in file:
                line, _, comment = line.partition('#') #Filter out comments
                if line.strip(): # If a non-blank line
                    entries = []
                    entries = tuple(line.split())
                    addressDict[entries[0]] = tuple(int(i) for i in entries[1:])  #Add or update key-val pair
                    #print("Entries:",entries[0])
        
        tempDict = {}
        iv_tempDict = {}
        with open(args.tempFile) as file:
            for line in file:
                line, _, comment = line.partition('#') #Filter out comments
                if line.strip(): # If a non-blank line
                    entries = []
                    entries = tuple(line.split())
                    tempDict[entries[0]] = int(entries[-1],0) #Dict to look up serial num from alias
                    iv_tempDict[int(entries[-1],0)] = entries[0] #Inverse dictionary to look up alias from serial num
                    
        persisting_vars = (args.slaveId, args.port, args.baudrate, args.numBoards,
                           TIMEOUT, addressDict, tempDict, iv_tempDict) #A tuple of vars to store in between commands
        
        var_file = open(varFileAbsDir, 'wb')
        pickle.dump(persisting_vars,var_file) #Save persisting variables in obj file
        
        #Test connections
        cntrl = dm(*persisting_vars[:-3])
        addressDict = persisting_vars[-3]
        tempDict = persisting_vars[-2]
        iv_tempDict = persisting_vars[-1]
        
        print('Channel List:')
        for key,chan in addressDict.items():
            try:
                #print(*chan)
                print('Alias: ',key,'\tChan #, DAC #, Board #: ',chan,'\t(DAC) Start Val: ',
                      dm.convertToActualV(cntrl.readV(cntrl.address(*chan))),'V', sep='')
            except KeyError:
                print('Error: DAC channel address',key,'not found')
                exit(1)
        
        numTemps = cntrl.initT()
        print('\nNumber of Temperature sensors on bus: ', numTemps)
        
        #Go through temp sensors on bus and make dict of serial num vs index
        print("Temperature Sensor Serial Numbers:")
        for i in range(numTemps):
            serialNum = cntrl.getTSerial(i) #index -> serial num
            #Now see if there's an alias for this serial number
            try:
                alias = iv_tempDict[int.from_bytes(serialNum,"big")]
                print(f"{alias}:\t0x{serialNum.hex()}")
            except KeyError:
                print(f"No Alias Found:\t0x{serialNum.hex()}")
                
    
    psr_init = subpsrs.add_parser('init', #aliases=['in']
                                        help='Initialize DAC communications. Read the DAC and temperature sensor '
                                        +'directory files. This must be called whenever one of those files is '
                                        +'modified. Use the directory files to specify a command line alias '
                                        +'for each DAC voltage output and temperature sensor.')
    psr_init.add_argument('-s','--slaveId', type=int, default=SLAVE_ID,
                             help='Specify the slave ID number for the Arduino. This must match the variable '
                             +f'SLAVE_ID in the Arduino code. {SLAVE_ID} by default.')
    psr_init.add_argument('-p','--port', type=str, default=COM_PORT,
                             help=f'Choose a serial port. {COM_PORT} by default.')
    psr_init.add_argument('-n','--numBoards', type=int, default=NUM_BOARDS,
                             help='Specify the number of DAC boards hooked up to the Arduino. This '
                             +f'must match the variable NUM_BOARDS in the Arduino code. {NUM_BOARDS} '
                             +'by default.')
    psr_init.add_argument('-b','--baudrate', type=int, default=BAUD_RATE,
                             help='Change the baudrate. This must match the variable '
                             +f'BAUD_RATE in the Arduino code. {BAUD_RATE} by default.')
    psr_init.add_argument('-a','--addressFile', type=str, default=DAC_DIR_FILE,
                             help='The address directory to specify the DAC channel mapping.')
    psr_init.add_argument('-t','--tempFile', type=str,default=TEMP_DIR_FILE,
                          help='The temperature sensor serial code directory '
                              +'to specify the temperature controller mapping. Make sure there are fewer '
                              +'temperature sensors on the bus then the variable NUM_TEMPS in the Arduino code.')
    psr_init.set_defaults(func=init)
    
    #powerUp command
    def powUp(args):            
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(*addressDict[chan])
                #print(channel)
                #print(addressDict)
                cntrl.powerUp(channel)
                print('(Ard)', chan,': \tPow =',bool(cntrl.getPower(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
            
    
    psr_powUp = subpsrs.add_parser('powerUp', aliases=['powUp'],
                                        help='Power up a channel')
    psr_powUp.add_argument('chan', type=str, nargs='*',
                              help="Aliases of DAC channels separated by a space or 'all'.")
    psr_powUp.set_defaults(func=powUp)
    
    #powerDown command
    def powDown(args):
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(channel)
                cntrl.powerDown(channel)
                print('(Ard)', chan,': \tPow =',bool(cntrl.getPower(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
            
    psr_powDown = subpsrs.add_parser('powerDown', aliases=['powDn','powDown'],
                                      help='Power down a channel.')
    psr_powDown.add_argument('chan', type=str, nargs='*',
                              help="Aliases of DAC channels separated by a space or 'all'.")
    psr_powDown.set_defaults(func=powDown)
    
    #getPower command
    def getPower(args):
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(channel)
                print('(Ard)', chan,': \tPow =',bool(cntrl.getPower(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
            
    psr_getPow= subpsrs.add_parser('getPower', aliases=['getPow','getP'],
                                      help='Return whether or not a channel is powered on, '
                                      'according to the last stored value in the Arduino.')
    psr_getPow.add_argument('chan', type=str, nargs='*',
                              help="Aliases of DAC channels separated by a space or 'all'.")
    psr_getPow.set_defaults(func=getPower)
    
    #getV command
    def getV(args):
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(channel)
                print('(Ard)', chan,': \tV =',dm.convertToActualV(cntrl.getV(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
    
    psr_getV = subpsrs.add_parser('getV',
                                   help='Returns the last commanded voltage stored on the Arduino')
    psr_getV.add_argument('chan', type=str, nargs='*',
                           help="Aliases of DAC channels separated by a space or 'all'.")
    psr_getV.set_defaults(func=getV)
    
    #readV command
    def readV(args):
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(channel)
                print('(DAC)', chan,': \tV = ',dm.convertToActualV(cntrl.readV(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
    
    psr_readV = subpsrs.add_parser('readV', aliases=['rdV'],
                                   help='Queries the DAC for actual voltage')
    psr_readV.add_argument('chan', type=str, nargs='*',
                           help="Aliases of DAC channels separated by a space or 'all'.")
    psr_readV.set_defaults(func=readV)
    
    
    #updateV command
    def updateV(args):
        cntrl, addressDict,_,_ = init_command()
        if(args.chan[0].lower()) == 'all': #If 'all' entered, use all the chans
            args.chan = list(addressDict.keys())
        for chan in args.chan:
            try:
                channel = cntrl.address(*addressDict[chan])
                #print(channel, args.newV)
                cntrl.updateV(channel, cntrl.convertToRawV(args.newV))
                print('(DAC)', chan,': \tV = ',dm.convertToActualV(cntrl.readV(channel)))
            except KeyError:
                print('Error: DAC channel address for',chan,'not found. See ' +
                      'DacDir.txt or the DAC directory file you specified for ' +
                      'a list of available DAC names.')
                cntrl.close()
                exit(1)
        cntrl.close()
    
    psr_updateV = subpsrs.add_parser('updateV', aliases=['newV'],
                                     help='Updates the voltage on the DAC channel')
    psr_updateV.add_argument('newV',type=float,
                             help="The new voltage to output.")
    psr_updateV.add_argument('chan', type=str, nargs='*',
                              help="Aliases of DAC channels separated by a space or 'all'.")
    psr_updateV.set_defaults(func=updateV)
    
    
    #readT command
    def readT(args):
        cntrl, addressDict,tempDict,iv_tempDict = init_command()
        numTemps = cntrl.initT()
        if(numTemps < 0):
            raise RuntimeError(f'Error in initializing temperature sensors;\
                               cntrl.initT() responded with: {numTemps}')
            cntrl.close(); exit(1)
        
        #Make a dictionary to get serial num -> index
        t_ser_dict = {}
        for i in range(numTemps):
            serialNum = cntrl.getTSerial(i) #index -> serial num
            t_ser_dict[int.from_bytes(serialNum,"big")] = i #inverse dict: serial num -> index
            
        if(args.alias[0].lower()) == 'all': #If 'all' entered, use all sensors on the bus
            args.alias = list(tempDict.keys())
            
        alias_to_index = {}
        for alias in args.alias:
            try:
                serialNum = tempDict[alias]
            except KeyError:
                print(f"The temperature sensor alias '{alias}' was not found in the "\
                      +"temperature sensor directory")
                cntrl.close()
                exit(1)
            try:
                index = t_ser_dict[serialNum]
                alias_to_index[alias] = index
            except KeyError:
                print(f"The temperature sensor with alias '{alias}' was not found "\
                      +"on the data bus.")
                cntrl.close()
                exit(1)
        
        for alias in args.alias:
            index = alias_to_index[alias]
            cntrl.recordT(index)
        time.sleep(0.75) #Wait for sensors to acquire temp values
        for alias in args.alias:
            index = alias_to_index[alias]
            if(not args.Fahrenheit): #default
                print(alias,': \tT = ', dm.convertToDegC(cntrl.getT(index)), 'C')
            else:
                print(alias,': \tT = ', 
                      dm.convertToDegC(cntrl.getT(index))*9/5 + 32, 'F')
                
        cntrl.close()
    
    psr_readT = subpsrs.add_parser('readT', aliases=['rdT'],
                                    help='Returns the temperature, in degrees Celsius, on the sensor.')
    psr_readT.add_argument('-F','--Fahrenheit', action='store_true',
                             help='Output in Fahrenheit instead of Celsius.')
    psr_readT.add_argument('alias', type=str, nargs='*',
                            help="Aliases of temperature sensors on data bus or 'all'.")
    psr_readT.set_defaults(func=readT)
    
    
    #numT command
    def numT(args):
        cntrl,_,_,_ = init_command()
        numTemps = cntrl.initT()
        if(numTemps < 0):
            raise RuntimeError(f'Error in initializing temperature sensors;\
                               cntrl.initT() responded with: {numTemps}')
            cntrl.close(); exit(1)
        print('Number of temp sensors = ',numTemps)            
        cntrl.close()
    
    psr_numT = subpsrs.add_parser('numTempSensors', aliases=['numT'],
                                  help="Returns the total number of temperature \
                                        sensors detected on the data bus. '-1' \
                                        denotes an error.")
    psr_numT.set_defaults(func=numT)
    
    
    #serT command
    def serT(args):
        cntrl, addressDict,tempDict,iv_tempDict = init_command()
        #Go through temp sensors on bus and make dict of serial num vs index
        numTemps = cntrl.initT()
        if(numTemps < 0):
            raise RuntimeError(f'Error in initializing temperature sensors;\
                               cntrl.initT() responded with: {numTemps}')
            cntrl.close(); exit(1)
        print("Temperature Sensor Serial Numbers:")
        for i in range(numTemps):
            serialNum = cntrl.getTSerial(i) #index -> serial num
            #Now see if there's an alias for this serial number
            try:
                alias = iv_tempDict[int.from_bytes(serialNum,"big")]
                print(f"{alias}:\t0x{serialNum.hex()}")
            except KeyError:
                print(f"No Alias Found:\t0x{serialNum.hex()}")
                cntrl.close()
                exit(1)
        cntrl.close()
        
    psr_serT = subpsrs.add_parser('tempSensorSerNums', aliases=['serT'],
                                  help="Returns the serial numbers for all temp "+
                                  "sensors detected on the data bus, as long as there "+
                                  "are fewer sensors than the value of the variable "+
                                  "NUM_TEMPS in the Arduino code.")
    psr_serT.set_defaults(func=serT)
    
    return psr

def main():
    ### PARSE COMMAND LINE AND EVALUATE
    args = return_parser().parse_args() #Parse the args
    
    if(bool(vars(args))): #Check if command argument supplied
        args.func(args)         #Call whatever function was selected
    else:
        raise ValueError('A valid command or option is required to run this script. ' +
                         'Use the option \'-h\' for a list of valid commands and options.')
        
if __name__ == '__main__':
    main()