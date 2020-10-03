# APTDacManager
A project to control the digital-analog converters (DACs) and temperature sensors on the
 WUSTL APT detector prototypes.



Use the controller by running the command line interface, cmdUI.py, on a computer connected
 over RS485 to an Arduino Mega running DacSlave.ino. The Arduino should also be linked over
 SPI to the boards containing the DAC chips. The SYNC pin on each DAC acts as a chip select,
 so each DAC gets a separate SYNC line, but all other lines may be daisychained together. See
 the [DacManager page](https://sites.physics.wustl.edu/APTwiki/index.php/DAC_Manager) on the
 WashU APT internal wiki for a schematic, required hardware, and an additional overview.
 
Be sure to use `from DacMaster import DacMaster` to import the python DacMaster class if you
 want to use the python DacMaster.py interface.

**Documentation:** <https://austinstover.github.io/APTDacManager>

**Required Packages:**
  - [MinimalModbus](https://github.com/pyhys/minimalmodbus)
  - [ArduinoModbusSlave](https://github.com/yaacov/ArduinoModbusSlave)
  - [DallasTemperature](https://github.com/milesburton/Arduino-Temperature-Control-Library)
  - [OneWire](https://www.pjrc.com/teensy/td_libs_OneWire.html)
  
**Tested with:**
  - Python				v3.7.6
  - Arduino				v1.8.13
  - MinimalModbus		v1.0.2
  - ArduinoModbusSlave	v2.0.0
  - DallasTemperature 	v3.9.0
  - OneWire 			v2.3.5
  
v0.5 adds command line interface commands to control DS18B20 temperature sensors.
v0.4 added a command line interface for DAC control.

**Command line subroutines:**
  - init
  - powerUp
  - powerDown
  - getPower
  - getV
  - readV
  - updateV
  - readT
  - numT
  - serT

**Getting Started**
  1. Install all required packages and upload DacSlave.ino to the Arduino. Ensure all hardwire is wired
  according to the schematic on the [APT wiki](https://sites.physics.wustl.edu/APTwiki/index.php/DAC_Manager). \
  MinimalModbus is a Python package and may be installed using pip or some other python package manager.
  ArduinoModbusSlave is a custom library that can be installed in the `Arduino\libraries` directory or
  using the "Add .ZIP library..." option in the Arduino IDE. DallasTemperature and OneWire may both be
  installed using the Arduino IDE Package Manager.
  
  2. Customize DacDir.txt to link DAC output channels with your desired command line aliases, and customize
  TempDir.txt to associate temperature sensors with aliases. You can also edit these files later and use the
  `init` subroutine to refresh. I suggest using the `serT` subroutine to discover temperature sensors and their
  serial numbers, and then adding these serial numbers with their corresponding aliases to the TempDir.txt document.
  3. Run the command line interface, starting with the `init` subroutine to initialize the serial communication
  options and reread DacDir.txt and TempDir.txt. Make sure to specify the correct COM port using the `-p` option.

To run the command line interface on Linux or Windows, type `python cmdUI.py [-h] {subroutine name} {arguments} {Alias 1} {Alias 2} ... {Alias N}` in the directory with cmdUI.py.
 Alternatively, run `python3 -m cmdUI [-h] ...` on Raspbian or `python -m cmdUI [-h] ...` on Windows or Linux in any directory if cmdUI.py is on the PYTHONPATH. Using "all" or
 "ALL" as the alias will apply the command to all DACs in DacDir.txt or all temperature sensors given an alias in tempDir.txt, depending on the command.

The DacDir.txt file specifies the list of available DAC aliases and their respective channel numbers (0-3), DAC numbers (0-1), and board numbers (0-3 by default). The TempDir.txt
 file specifies temperature sensor aliases and their corresponding unique 64-bit serial codes.
