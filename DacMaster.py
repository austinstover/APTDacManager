'''
This program defines a class to control DACs hosted by an Arduino slave via the Modbus
RTU RS485 protocol for the APT experiment CERN prototype

..  moduleauthor:: Austin Stover <stover.a@wustl.edu>
    :date: June 2018
'''

import minimalmodbus as mb

class DacMaster:
    """This class defines methods to send and receive commands and data via Modbus RTU
    RS485 to a slave that talks to a DAC using an SPI interface, to be used with
    DacSlave.ino
    """
    
    def __init__(self, slaveId, port, baudrate, numBoards=1, timeout=0.05):
        """Instantiates a DacMaster using the Modbus RTU protocol over RS458
        
        :param slaveId: The ID number to use for the slave
        :param port: The serial port to use
        :param baudrate: Compatible baud rates: 4800, 9600, 14400, 19200, 28800
        :param timeout: The max. length of time to wait for a slave to respond (s)
        :param numBoards: The number of DAC boards hooked up to the slave
        """
        mb.BAUDRATE = baudrate
        mb.TIMEOUT = timeout
        self.slave = mb.Instrument(port, slaveId)
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
        """Returns the voltage for the DAC channel in the slave holding register

        :param address: The address of the DAC channel
        :returns: The voltage held in the slave
        """
        return self.slave.read_register(address, functioncode=3)

    def readV(self, address):
        """Should return the approximate DAC input register voltage
        WARNING: This may not return the exact voltage held in the input register, since
        the slave is reading the DAC on the wrong side of the CLK signal. This method
        should only be used to check the DAC is operating in general, but not for
        exact reads.
            
        :param address: The address of the DAC channel
        :returns: The approximate voltage in the DAC channel input register
        """
        return self.slave.read_register(address, functioncode=4)

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

    @staticmethod
    def convertToActualV(rawV):
        """Converts the input raw 12-bit voltage to the floating-point value

        :param rawV: The 12-bit unsigned integer output by many DacMaster functions
        :returns: The floating-point equivalent of rawV
        """
        return rawV * 60.0/4096.0

    @staticmethod
    def convertToRawV(actualV): #TODO: Ensure actualV is non-negative
        """
        Converts a floating-point voltage to its raw 12-bit value to input into many
        DacMaster functions
        :param actualV: The floating-point voltage value to convert
        :returns: The 12-bit raw voltage equivalent of actualV
        """
        rawV = (int)(actualV * 4096.0/60.0)
        return rawV if rawV < 4096 else 4095 #rawV must be a 12 bit number or less

def main():
    """A DacMaster Demo Program"""
    slaveId = 0
    port = 'COM4'
    baudrate = 9600
    dacChan = 0
    dacNum = 0
    voltage = DacMaster.convertToRawV(5.00)
    
    cntrl = DacMaster(slaveId, port, baudrate)
    dacAddress = cntrl.address(dacChan, dacNum)

    print("dacAddress: ", dacAddress)
    cntrl.updateV(dacAddress, voltage)
    print("rawV: ", bin(voltage))
    cntrl.powerUp(dacAddress)
    print("getV: ", DacMaster.convertToActualV(cntrl.getV(dacAddress)))
    print("readV: ", DacMaster.convertToActualV(cntrl.readV(dacAddress)))

if __name__ == '__main__':
    main()
