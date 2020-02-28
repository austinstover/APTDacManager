'''
This program defines a class to control DACs hosted by an Arduino slave via the Modbus
RTU RS485 protocol for the APT experiment CERN prototype.

..  moduleauthor:: Austin Stover <stover.a@wustl.edu>
    :date: June 2018

Copyright (C) 2018  Austin Stover

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
#mb.CLOSE_PORT_AFTER_EACH_CALL=True

class DacMaster:
    """This class defines methods to send and receive commands to the slave.

    The constructor instantiates a DacMaster using the Modbus RTU protocol over RS485.
    
    :param slaveId: The ID number to use for the slave
    :param port: The serial port to use
    :param baudrate: Compatible baud rates: 4800, 9600, 14400, 19200, 28800
    :param timeout: The max. length of time to wait for a slave to respond (s)
    :param numBoards: The number of DAC boards hooked up to the slave
    """
    
    def __init__(self, slaveId, port, baudrate, numBoards=1, timeout=0.05):
        mb.BAUDRATE = baudrate
        mb.TIMEOUT = timeout
        self.slave = mb.Instrument(port, slaveId)
        self.numBoards = numBoards
        
    def updateV(self, chanAddr, newRawV):
        """Updates the voltage in the DAC channel input register, then updates the DAC
        register by pulsing the LDAC pin. The DAC channel must then be powered on to
        output the voltage.

        :param newV: The raw integer voltage with which to update the DAC channel
        :param chanAddr: The address of the DAC channel
        """
        self.slave.write_register(chanAddr, newRawV, functioncode=6)

    def getV(self, chanAddr):
        """Returns the voltage for the DAC channel in the slave holding register

        :param chanAddr: The address of the DAC channel
        :returns: The voltage held in the slave
        """
        return self.slave.read_register(chanAddr, functioncode=3)

    def readV(self, chanAddr):
        """Should return the approximate DAC input register voltage
        WARNING: This may not return the exact voltage held in the input register, since
        the slave is reading the DAC on the wrong side of the CLK signal. This method
        should only be used to check the DAC is operating in general, but not for
        exact reads.
            
        :param chanAddr: The address of the DAC channel
        :returns: The approximate voltage in the DAC channel input register
        """
        return self.slave.read_register(chanAddr, functioncode=4)

    def powerUp(self, chanAddr):
        """Powers on the DAC channel analog output.
        
        :param chanAddr: The address of the DAC channel
        """
        self.slave.write_bit(chanAddr, 1, functioncode=5)

    def powerDown(self, chanAddr):
        """Powers off the DAC channel analog output
        
        :param chanAddr: The address of the DAC channel
        """
        self.slave.write_bit(chanAddr, 0, functioncode=5)

    def getPower(self, chanAddr):
        """Returns whether power to the DAC channel analog output
        is on or off in the slave coil
        
        :param chanAddr: The address of the DAC channel
        :returns: True if power to the analog channel was switched on; False if it
            was switched off. The DACs default to off.
        """
        return self.slave.read_bit(chanAddr, functioncode=1)
                                   
    def chanAddr(self, boardAddress, dacNum):
        """Outputs the address to use given the DAC board address and DAC
        number on that board. The board address is the input to the chip select
        decoder.

        :param boardAddress: Specifies the channel on the DAC (0 through 2^7-1)
        :param dacNum: Specifies the DAC on the board (0 through 3)
        :returns: The DAC channel address
        """
        return 4*boardAddress + dacNum #self.numBoards*4*2*sipmChan + (4*2*boardNum + (4*dacNum + dacChan))
    
#    def address(self, dacChan, dacNum, boardNum=0, sipmChan=0):
#        """Outputs the address to use given the DAC channel IDs
#
#        :param dacChan: Specifies the channel on the DAC (0-3)
#        :param dacNum: Specifies the DAC on the board (0-1)
#        :param boardNum: Specifies the board
#        :param sipmChan: Specifies the SiPM channel
#        :returns: The DAC channel address
#        """
#        return %self.numBoards*4*2*sipmChan + (4*2*boardNum + (4*dacNum + dacChan))

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

def main():
    """A DacMaster Demo Program: This updates the specified DAC with the
    voltage, powers on the analog output to reach that voltage, and then reads
    back the voltage both in the holding register on the slave and the input
    register on the DAC.
    """
    slaveId = 0
    port = 'COM4'
    baudrate = 9600
    dacChan = 0
    dacNum = 0

    newVoltage = 5.00
    
    rawV = DacMaster.convertToRawV(newVoltage)
    cntrl = DacMaster(slaveId, port, baudrate)
    
    '''Gets the address for the DAC based on the current DAC channel, number, board, and
    SiPM channel'''
    dacAddress = cntrl.chanAddr(dacChan, dacNum)

    print("dacAddress: ", dacAddress)
    cntrl.updateV(dacAddress, rawV)
    print("rawV: ", bin(rawV))
    cntrl.powerUp(dacAddress)
    print("getV: ", DacMaster.convertToActualV(cntrl.getV(dacAddress)))
    print("readV: ", DacMaster.convertToActualV(cntrl.readV(dacAddress)))

if __name__ == '__main__':
    main()
