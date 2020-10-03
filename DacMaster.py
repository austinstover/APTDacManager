'''
This program defines a class to control DACs hosted by an Arduino slave via the Modbus
RTU RS485 protocol for the APT experiment CERN prototype. It also controls
DS18B20 temperature through the Arduino using the 1-wire protocol.

..  moduleauthor:: Austin Stover <stover.a@wustl.edu>
    :date: June 2018-Sept 2020

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
'''

import minimalmodbus as mb
import serial
#mb.CLOSE_PORT_AFTER_EACH_CALL=True

class DacMaster:
    """This class defines methods to send and receive commands to the slave.

    The constructor instantiates a DacMaster using the Modbus RTU protocol over RS485.
    
    :param slaveId: The ID number to use for the slave
    :param port: The serial port to use
    :param baudrate: Compatible baud rates: 4800, 9600, 14400, 19200, 28800
    :param timeout: The max. length of time to wait for a slave to respond (s)
    :param numBoards: The number of DAC boards hooked up to the slave. This
           must be the same as the variable NUM_BOARDS in the Arduino code.
    """
    
    def __init__(self, slaveId, port, baudrate, numBoards=1, timeout=0.3):
        self.slave = mb.Instrument(port, slaveId)
        self.slave.serial.baudrate = baudrate
        self.slave.serial.timeout = timeout
        self.slave.serial.bytesize = 8
        self.slave.serial.parity = serial.PARITY_NONE
        self.slave.serial.stopbits = 1
        self.numBoards = numBoards
        
    def updateV(self, address, newRawV):
        """Updates the voltage in the DAC channel input register, then updates the DAC
        register by pulsing the LDAC pin. The DAC channel must then be powered on to
        output the voltage.

        :param newV: The raw integer voltage with which to update the DAC channel
        :param address: The address of the DAC channel
        """
        self.slave.write_register(address, newRawV, functioncode=6)

    def getV(self, address):
        """Returns the voltage for the DAC channel stored in the slave holding register

        :param address: The address of the DAC channel
        :returns: The voltage held in the slave
        """
        return self.slave.read_register(address, functioncode=3)

    def readV(self, address):
        """Returns the approximate DAC input register voltage
        WARNING: The lsb of this voltage is the second-to-last bit recorded
            
        :param address: The address of the DAC channel
        :returns: The approximate voltage in the DAC channel input register
        """
        return self.slave.read_register(address, functioncode=4)
    
    def initT(self):
        """Initializes temperature sensor addresses and indices inside Arduino
        
        :returns: Number of temperature sensors on bus detected and addressed
        """
        address = self.numBoards*2*4
        numSensors_uint16 = self.slave.read_register(address, functioncode=4)
        return numSensors_uint16 - 32768 #Convert 16-bit uint back to int
    
    def getTSerial(self, i):
        """Outputs the 64-bit serial code of the temperature sensor with the
        given index. The output is a bytes object.
        
        :returns: The 64-bit OneWire sensor address as a bytes object
        """
        address = 1 + self.numBoards*2*4 + int(i)*4
        
        #Concatenate byte hex vals to get address
        return b''.join([self.slave.read_register(address+i, functioncode=3)
                                   .to_bytes(2,"big") for i in range(0,4)]) 
    
    def getT(self, i):
        """Returns the recorded raw temperature from the ith temperature sensor
        on the temp sensor data bus. Must wait 750ms max after recordT() to get
        updated values (for 12-bit precision).
        
        :param i: The index (starting at 0) of the temp sensor to read. The 0th
            sensor is closest on the bus to the Arduino
        :returns: The raw temperature reading
        """
        if(i<0):
            raise ValueError(f'Temperature sensor index must be a positive integer, not {i}')
        address = 1 + self.numBoards*2*4 + int(i)*4
        temp_uint16 = self.slave.read_register(address, functioncode=4)
        return temp_uint16 - 32768 #Convert 16-bit uint back to int
    
    def recordT(self, i):
        """Records the temperature on the ith temperature sensor on the temp
        sensor data bus
        
        :param i: The index (starting at 0) of the temp sensor to read. The 0th
            sensor is closest on the bus to the Arduino
        :returns: False if sensor is disconnected; True otherwise
        """
        address = 1 + self.numBoards*2*4 + int(i)*4
        return self.slave.read_bit(address, functioncode=1)

    def powerUp(self, address):
        """Powers on the DAC channel analog output.
        
        :param address: The address of the DAC channel
        """
        self.slave.write_bit(address, 1, functioncode=5)

    def powerDown(self, address):
        """Powers off the DAC channel analog output
        
        :param address: The address of the DAC channel
        """
        self.slave.write_bit(address, 0, functioncode=5)

    def getPower(self, address):
        """Returns whether power to the DAC channel analog output
        is on or off in the slave coil
        
        :param address: The address of the DAC channel
        :returns: True if power to the analog channel was switched on; False if it
            was switched off. The DACs default to off.
        """
        return self.slave.read_bit(address, functioncode=1)
                                   
    def address(self, dacChan, dacNum, boardNum=0, sipmChan=0):
        """Outputs the address to use given the DAC channel IDs

        :param dacChan: Specifies the channel on the DAC (0-3)
        :param dacNum: Specifies the DAC on the board (0-1)
        :param boardNum: Specifies the board
        :param sipmChan: Specifies the SiPM channel
        :returns: The DAC channel address
        """
        return self.numBoards*4*2*sipmChan + (4*2*boardNum + (4*dacNum + dacChan))
    
    def close(self):
        """Closes the serial port
        """
        self.slave.serial.close()

    @staticmethod
    def convertToActualV(rawV):
        """Converts the input raw 12-bit voltage to the floating-point value

        :param rawV: The 12-bit unsigned integer output by many DacMaster functions
        :returns: The floating-point equivalent of rawV
        """
        return rawV * 60.0/4096.0

    @staticmethod
    def convertToRawV(actualV):
        """
        Converts a floating-point voltage (in volts, between 0 and 60 inclusive) to its
        raw 12-bit value to input into many DacMaster functions
        :param actualV: The floating-point voltage value to convert
        :returns: The 12-bit raw voltage equivalent of actualV
        """
        if (actualV < 0 or actualV > 60):
            raise ValueError('The voltage to convert must be between 0 and 60 inclusive')
        rawV = (int)(actualV * 4096.0/60.0)
        return rawV if rawV < 4096 else 4095 #rawV must be a 12 bit number or less
    
    @staticmethod
    def convertToDegC(rawTemp):
        """Converts the input raw temperature to the floating-point value

        :param rawTemp: The 16-bit temp output from the DallasTemperature library
        :returns: The floating-point equivalent of rawTemp
        """
        TEMP_DEVICE_DISCONNECTED_RAW = -7040
        TEMP_DEVICE_DISCONNECTED_C = -127
        if(rawTemp <= TEMP_DEVICE_DISCONNECTED_RAW):
            return TEMP_DEVICE_DISCONNECTED_C
        #C = RAW/128
        return rawTemp * 0.0078125

def main():
    """A DacMaster Demo Program: This updates the specified DAC with the
    voltage, powers on the analog output to reach that voltage, and then reads
    back the voltage both in the holding register on the slave and the input
    register on the DAC. It also reads the temperature on the chosen
    temperature sensor and prints the number of temperature sensors detected on
    the data bus.
    """
    slaveId = 1
    port = 'COM13'
    baudrate = 9600
    dacChan = 0
    dacNum = 0
    numBoards=4

    newVoltage = 5.00
    tempInd = 2
    
    rawV = DacMaster.convertToRawV(newVoltage)
    cntrl = DacMaster(slaveId, port, baudrate,numBoards)
    
    '''Gets the address for the DAC based on the current DAC channel, number, board, and
    SiPM channel'''
    dacAddress = cntrl.address(dacChan, dacNum)

    print("dacAddress: ", dacAddress)
    cntrl.updateV(dacAddress, rawV)
    print("rawV: ", bin(rawV))
    cntrl.powerUp(dacAddress)
    print("getV: ", DacMaster.convertToActualV(cntrl.getV(dacAddress)))
    print("readV: ", DacMaster.convertToActualV(cntrl.readV(dacAddress)))
    
    print("numTemps: ", cntrl.initT())
    print("addr: ", "0x"+cntrl.getTSerial(tempInd).hex())
    cntrl.recordT(tempInd)
    import time
    time.sleep(0.75) #Sleep 750ms to wait for conversion
    print("readTemp: ", DacMaster.convertToDegC(cntrl.getT(tempInd)))
    cntrl.close()
if __name__ == '__main__':
    main()
