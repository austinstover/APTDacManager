# APTDacManager
A project to control the digital-analog converters (DACs) on the WUSTL APT CERN-test
 detector prototype

To implement, DacMaster.py is run on a computer connected over RS485 to an Arduino Mega
 running DacSlave.py, which is in turn linked over SPI to the boards containing the
 DACs. The SYNC pin on each DAC acts as a chip select, so each DAC gets a separate SYNC
 line, but all other lines may be daisychained together.
 
Be sure to use `from DacMaster import DacMaster` to import the python class.

**Documentation:** <https://austinstover.github.io/APTDacManager>

**Required Packages:**
  - [MinimalModbus](https://github.com/pyhys/minimalmodbus)
  - [ArduinoModbusSlave](https://github.com/yaacov/ArduinoModbusSlave)
  
Tested with:
  - Python				v3.5.3
  - Arduino				v1.8.3
  - MinimalModbus		v0.7.0
  - ArduinoModbusSlave	v2.0.0
  
  
v0.4 comes with a brand new command line interface to control all of the DACs. The command line subroutines consist of:

  - init
  - powerUp
  - powerDown
  - getPower
  - getV
  - readV
  - updateV
  
To run the command line interface on raspbian, type "python3 cmdUI.py [-h] {subroutine name} {DAC Alias 1} {DAC Alias 2} ... {DAC Alias N}:" in the directory with cmdUI.py.

The DacDir.txt file specifies the list of available DAC aliases and their respective channel numbers (0-3), DAC numbers (0-1), and board numbers (0-3 by default). Using "all" or "ALL" as the alias will apply the command to all DACs in DacDir.txt.

v0.4 also includes code from Robogaia to control the temperature controller, *which is not covered under the GNU license*. This code (and the hardware) has been modified slightly to allow for colder temperature readings and setting. The minimum temperature that can be read is now ~-21F or -29C.

Further documentation to come.
