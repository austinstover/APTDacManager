# APTDacManager
A project to control the digital-analog converters (DACs) on the WUSTL APT CERN-test
 detector prototype

To implement, DacMaster.py is run on a computer connected over RS485 to an Arduino Mega
 running DacSlave.py, which is in turn linked over SPI to the boards containing the
 DACs. The SYNC pin on each DAC acts as a chip select, so each DAC gets a separate SYNC
 line, but all other lines may be daisychained together.

**Documentation:** <https://austinstover.github.io/APTDacManager>

**Required Packages:**
  - [MinimalModbus](https://github.com/pyhys/minimalmodbus)
  - [ArduinoModbusSlave](https://github.com/yaacov/ArduinoModbusSlave)