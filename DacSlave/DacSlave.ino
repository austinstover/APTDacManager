/**
 * @file DacSlave.ino
 * @author Austin Stover
 * @date June 2018
 * 
 * This program communicates with a computer running DacMaster.py using the Modbus 
 * RS485 protocol to manage AD5504 DACs for the APT experiment. Now includes the
 * ability to query several DS18B20 temperature sensors and report entire 64-bit addresses.
 * 
 * Copyright (C) 2018  Austin Stover
 * 
 * This file is part of APTDacManager.
 * 
 *     APTDacManager is free software: you can redistribute it and/or modify
 *     it under the terms of the GNU General Public License as published by
 *     the Free Software Foundation, either version 3 of the License, or
 *     (at your option) any later version.
 * 
 *     APTDacManager is distributed in the hope that it will be useful,
 *     but WITHOUT ANY WARRANTY; without even the implied warranty of
 *     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *     GNU General Public License for more details.
 * 
 *     You should have received a copy of the GNU General Public License
 *     along with APTDacManager.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <SPI.h>
#include <ModbusSlave.h> //Custom library
#include <OneWire.h> 
#include <DallasTemperature.h>
#define TEMP_DEVICE_DISCONNECTED_RAW -7040
//typedef uint8_t TempAddr[8]; //The address type for the temp sensors, which have their own addressing system

typedef union
{
  uint8_t  bytes[8];  //Represent as bytes for use with the DallasTemperature library
  uint16_t shorts[4]; //Represent as 16 bit ints for sending over SPI
} TempAddr;


const int SLAVE_ID = 1;        ///< This specifies which Arduino to which the master will talk
const int BAUD_RATE = 9600;

const int TX_PIN = 2;          ///< This is the DE/RE pin for the Serial to RS485 converter
const int LDAC_PIN = 47;       ///< This pin is pulsed to move data from input to DAC register
const int CLR_PIN = 45;
const int TEMP_BUS_PIN = 3;    ///< The data pin for the temperature sensor data bus

const uint8_t NUM_BOARDS = 4;  ///< Max number of DAC boards to connect to
const uint8_t NUM_TEMPS  = 16; ///< Max number of temperature sensors on the bus

// NOTE: On the Arduino Mega 2560, pin 52 = SCK, 50 = MISO, 51 = MOSI, 53 = SS (So must be left alone during SPI comm)
    
/**
 * @brief CS_ARRAY[] relates the DAC channel chip select outputs to specific Arduino pins.
 * 
 * There is 1 pin per DAC and 2 DACs per board, and NUM_BOARDS DAC boards. The first 2 
 * pins in the array therefore denote the chip selects for DACs 0 and 1 on board 0. The 
 * next two pins are 0 and 1 on board 1, etc. as illustrated below. The element index
 * is related to these parameters by the following equation:
 * dacV Index = address = 4*2*boardNum + 4*dacNum + dacChan
*/
const uint8_t CS_ARRAY_LEN = NUM_BOARDS*2;
const uint8_t CS_ARRAY[CS_ARRAY_LEN] = {46,44,43,42,41,40,39,38};
// Element index:                        0  1  2  3  4  5 ... 
// DAC Number:                           0  1  0  1  0  1 ... 0  1
// Board Number:                         0     1     2    ... n

const uint16_t CONTROL_ARRAY_LEN = NUM_BOARDS*2;

/**
 * @brief controlArray[] saves the states of the DAC control registers in the Arduino.
 * 
 * controlArray elements are numbered the same way as CS_ARRAY[] elements.
 * controlArray[i] denotes the same DAC channel as CS_ARRAY[i]. The element index is
 * related to its parameters by the following equation (using integer division):
 * controlArray Index = address / 4 = 2*boardNum + dacNum
 */
uint16_t controlArray[CONTROL_ARRAY_LEN]; //Saves the states of the control registers
    
const SPISettings spiSet{125000, MSBFIRST, SPI_MODE0};


const uint16_t DAC_V_LEN = NUM_BOARDS*2*4;

/**
 * @brief dacV[] holds the voltage for each DAC channel
 * 
 * There are 4 times as many entries in this array as there are in CS_ARRAY[] or 
 * controlArray[], since there are 4 channels per DAC. There are therefore 4 elements
 * per DAC number, as illustrated. To get the controlArray element from the dacV
 * element, just integer divide by 4. The DAC channel can also be determined from the
 * dacV element by performing modulo 4 on the element #.
 */
uint16_t dacV[DAC_V_LEN] = { 0 }; //Init all Vs to 0
// Element index:            0  1  2  3  4  5  6  7  8 ...
// DAC Channel:              0  1  2  3  0  1  2  3  0 ...
// DAC Number:               0           1           0 ...
// Board Number:             0                       1 ...


const uint16_t TEMP_ADDR_ARRAY_LEN = NUM_TEMPS;
/**
 * @brief tempAddrArray holds the temperature sensor addresses for each index
 * 
 * The 0th element holds the address for index 0: the closest temperature sensor to
 * the Arduino on the bus
 */
TempAddr tempAddrArray[TEMP_ADDR_ARRAY_LEN] = { 0 };


//Connect the RS485 communication line to the below Serial port
Modbus slave(Serial1, SLAVE_ID, TX_PIN);

//Setup DS18B20 temperature sensors
OneWire oneWire(TEMP_BUS_PIN); 
DallasTemperature temp_sensors(&oneWire);


void setup()
{
  //For serial monitor output. Disable print statements after debugging to speed up program
  //Serial.begin(115200); 

  Serial1.begin(BAUD_RATE, SERIAL_8N1);
  slave.begin(BAUD_RATE);

  //Initialize TX_PIN to receive messages
  pinMode(TX_PIN, OUTPUT);
  digitalWrite(TX_PIN, LOW);
  //Initialize other pins
  pinMode(LDAC_PIN, OUTPUT);
  digitalWrite(LDAC_PIN, HIGH);
  pinMode(CLR_PIN, OUTPUT);
  digitalWrite(CLR_PIN, HIGH);
  
  for(int i = 0; i < CONTROL_ARRAY_LEN; i++)
  { //Initialize control register commands to all Dacs off
    controlArray[i] = 0b0111000000000000;
  }
  for(int j = 0; j < CS_ARRAY_LEN; j++)
  { //Initialize chip select pins
    pinMode(CS_ARRAY[j], OUTPUT);
    digitalWrite(CS_ARRAY[j], HIGH);
  }
  
  SPI.begin();

  //Callback handler function declarations
  slave.cbVector[CB_READ_COILS] = readCoil;
  slave.cbVector[CB_WRITE_COILS] = writeCoil;
  slave.cbVector[CB_READ_REGISTERS] = readReg;
  slave.cbVector[CB_WRITE_REGISTERS] = writeReg;

  temp_sensors.setWaitForConversion(false);
}

void loop()
{
  //Runs the Modbus input/output and associated actions (detailed in the modbus callback functions)
  slave.poll();
}

// ###################################################################
// #################### MODBUS CALLBACK FUNCTIONS ####################
// ###################################################################
/*
 * These functions will get called when a modbus message is received with the
 * function codes associated with their cbVector[]. DO NOT CALL THESE FUNCTIONS.
 * They are to be called within the ModbusSlave library only.
 */

/**
 * Callback function for a single holding register write (input registers can only be read)
 */
uint8_t writeReg(uint8_t fc, uint16_t address, uint16_t length)
{
  if(fc == FC_WRITE_REGISTER) //Writing a holding register updates the voltage on a DAC channel
  { //Holding regs are 16 bit read/write
    //Serial.print("1. "); Serial.print(address);
    if(address < DAC_V_LEN)
    {
      //Serial.print("\t2. "); Serial.print(slave.readRegisterFromBuffer(0));
      //Serial.print("\t3. "); Serial.println(DAC_V_LEN);
      updateV(slave.readRegisterFromBuffer(0), address);
      return STATUS_OK;
    }
  }
  else
    return STATUS_ILLEGAL_FUNCTION;
}

/**
 * Callback function for input/holding register reads
 */
uint8_t readReg(uint8_t fc, uint16_t address, uint16_t length)
{
  if(fc == FC_READ_HOLDING_REGISTERS) //Reading a holding register returns the voltage in the register
  { //Holding regs are 16 bit read/write
    if(address < DAC_V_LEN)
    {
      slave.writeRegisterToBuffer(0, getV(address));
      return STATUS_OK;
    }
    else if(address > DAC_V_LEN and address <= DAC_V_LEN + TEMP_ADDR_ARRAY_LEN*4)
    {
      slave.writeRegisterToBuffer(0, getTAddrShort(address));
      return STATUS_OK;
    }
    else
      return STATUS_ILLEGAL_DATA_ADDRESS;
  }
  else if(fc == FC_READ_INPUT_REGISTERS)
  { //Reading an input register reads the voltage from a DAC register
    //  or reads a temperature sensor, depending on the address
    //Input regs are 16 bit read-only
    if(address < DAC_V_LEN)
    {
      slave.writeRegisterToBuffer(0, readV(address));
      return STATUS_OK;
    }
    else if(address == DAC_V_LEN)
    {
      int16_t numSensors_int16 = initTs();
      slave.writeRegisterToBuffer( 0, (uint16_t)(((int32_t)numSensors_int16)+32768) );
      return STATUS_OK;
    }
    else if(address > DAC_V_LEN and address <= DAC_V_LEN + TEMP_ADDR_ARRAY_LEN*4)
    { 
      //Read (address-n)th temp sensor on temp data bus if address doesn't
      // correspond to a DAC, where n=DAC_V_LEN
      //Serial.print("\t11. "); Serial.print(address);
      slave.writeRegisterToBuffer(0, (uint16_t)(getT(address)));
      return STATUS_OK;
    }
  }
  else
    return STATUS_ILLEGAL_FUNCTION;
}

/**
 * Callback function for writing single bits to turn on/off DAC channel analog outputs
 */
uint8_t writeCoil(uint8_t fc, uint16_t address, uint16_t length)
{ //Coils are 1 bit read/write
  if(fc == FC_WRITE_COIL)
  {
    if(address < DAC_V_LEN)
    {
      power(slave.readCoilFromBuffer(0), address);
      return STATUS_OK;
    }
    else
      return STATUS_ILLEGAL_DATA_ADDRESS;
  }
  else
    return STATUS_ILLEGAL_FUNCTION;
}

/**
 * Callback function for reading single bits returns the DAC channel power boolean in the coil
 */
uint8_t readCoil(uint8_t fc, uint16_t address, uint16_t length)
{ //Coils are 1 bit read/write
  if(fc == FC_READ_COILS)
  {
    if(address < DAC_V_LEN)
    {
      slave.writeCoilToBuffer(0, getPower(address));
      return STATUS_OK;
    }
    else if(address > DAC_V_LEN and address <= DAC_V_LEN + TEMP_ADDR_ARRAY_LEN)
    {
      slave.writeCoilToBuffer(0, recordT(address));
      return STATUS_OK;
    }
    else
      return STATUS_ILLEGAL_DATA_ADDRESS;
  }
  else
    return STATUS_ILLEGAL_FUNCTION;
}

// ###############################################################
// #################### DAC CONTROL FUNCTIONS ####################
// ###############################################################

/**
 * Updates the voltage in the DAC channel input and DAC register
 * @param newV The new raw voltage to command
 * @param address The DAC channel address
 */
void updateV(uint16_t newV, uint16_t address)
{
  dacV[address] = newV < 4096 ? newV : 4095; //newV must be a 12-bit number or less
  uint8_t csPin = CS_ARRAY[address / 4];
  //Serial.print("1. "); Serial.print(address);
  //Serial.print("\t2. "); Serial.print(address /4);
  //Serial.print("\t3. "); Serial.print(csPin);
  //Serial.print("\t4. "); Serial.print(address % 4,BIN);
  //Serial.print("\t5. "); Serial.print((address+1) % 4,BIN);
  //Serial.print("\t6. "); Serial.print((address % 4)+1,BIN);
  //Serial.print("\t7. "); Serial.print(newV % 4096,BIN);
  //Creates the input register byte
  uint16_t updateVoltageWord = (newV % 4096) + (((address % 4)+1) << 12);
  //Serial.print("\t8. "); Serial.println(updateVoltageWord, BIN);
  SPI.beginTransaction(spiSet);
  
  digitalWrite(csPin, LOW); //Hold SYNC low on this DAC to update input register
  delayMicroseconds(1);
  SPI.transfer16(updateVoltageWord);
  delayMicroseconds(1);
  digitalWrite(csPin, HIGH);
  
  digitalWrite(LDAC_PIN, LOW); //Write input register data to DAC register by pulsing LDAC
  delayMicroseconds(1);
  digitalWrite(LDAC_PIN, HIGH);
  
  SPI.endTransaction();
}

/**
 * Returns the DAC channel voltage currently in the holding register
 * @return The raw voltage currently stored in the holding register
 */
uint16_t getV(uint16_t address)
{
  return dacV[address];
}

/**
 * Powers up or down a DAC analog channel
 * @param powerOn True if power is desired; false if not
 * @param address The DAC channel address
 */
void power(bool powerOn, uint16_t address)
{
  //This is the saved control register value for the DAC
  uint16_t powWord = controlArray[address / 4];
  uint16_t nopWord = 0; //Send a null after writing to control reg
  
  uint16_t csPin = CS_ARRAY[address / 4];

  //This byte picks out the power-up/down bit for the DAC channel
  uint16_t bitLoc = _BV(address % 4 + 2);

  //If you want to power up the channel, set the bit to 1; else 0
  powWord = powerOn ? powWord | bitLoc : powWord & ~bitLoc;
  //Now save the control register value
  controlArray[address / 4] = powWord;
  
  SPI.beginTransaction(spiSet);
  
  digitalWrite(csPin, LOW);
  delayMicroseconds(1);
  SPI.transfer16(powWord);
  SPI.transfer16(nopWord);
  delayMicroseconds(1);
  digitalWrite(csPin, HIGH);
  
  SPI.endTransaction();
}

/**
 * Returns whether the DAC channel is powered on or off based on its control byte
 * @param address The DAC channel address
 * @return True if on; false if off
 */
bool getPower(uint16_t address)
{
  //Serial.print("controlArray: "); Serial.print(controlArray[address / 4], BIN);
  return controlArray[address / 4] & _BV(address % 4 + 2);
}

/**
 * Reads input register voltage from the specified channel
 * 
 * NOTE: This may not return the exact value from the input register. It may be off by a single LSB.
 * 
 *  @param address The DAC channel address
 *  @return The raw voltage read from the DAC channel's input register
 */
uint16_t readV(uint16_t address)
{
  uint8_t csPin = CS_ARRAY[address / 4];
  uint16_t readVWord = 0b1000000000000000 + (((address % 4) + 1) << 12);
  //Serial.print("\t9. "); Serial.println(readVWord, BIN);
  SPI.beginTransaction(spiSet);
  
  digitalWrite(csPin, LOW);
  delayMicroseconds(1);
  uint16_t vRead = (SPI.transfer16(readVWord) << 1) % 4096; //Leftshift one to correct for reading on wrong side of clk cycle
  delayMicroseconds(1);
  digitalWrite(csPin, HIGH);
  
  SPI.endTransaction();
  //Serial.print("\t10. "); Serial.println(vRead, BIN);
  return vRead;
}


/**
 * Initializes temperature sensors by finding the addresses of all sensors on the bus
 * 
 * @return The number of sensors found on the bus or -1 if there is an error with getting an address
 */
int16_t initTs()
{
  temp_sensors.begin(); //Initialize or re-initialize temp sensors
  memset(tempAddrArray, 0, sizeof(tempAddrArray)); //Reset the temp sensor addresses
  
  uint8_t numDevices = temp_sensors.getDeviceCount();
  //Serial.print("\tNum Sensors: "); Serial.print(numDevices);
  
  bool notFound = 0;
  for(uint16_t index = 0; index < min(numDevices,TEMP_ADDR_ARRAY_LEN); index++) //Loop through sensors on data bus
  {
    notFound += !temp_sensors.getAddress(tempAddrArray[index].bytes, index); 
  }
  if(notFound) //notFound nonzero if can't find a sensor
    return -1;
  else
    return ((int16_t) numDevices);
}

/**
 * Returns 16 bits of the 64-bit temperature controller address
 */
uint16_t getTAddrShort(uint16_t address)
{
  uint16_t index       = (address - 1 - DAC_V_LEN) / 4; //Which temperature controller do I want?
  uint16_t short_index = (address - 1 - DAC_V_LEN) % 4; //Which 16 bits of the temperature controller address do I want?

  //Serial.print("TAddr: "); Serial.print(index); Serial.print(", "); Serial.print(short_index); Serial.print(": ");
  //Serial.print(tempAddrArray[index].shorts[short_index], HEX); Serial.println();
  
  return tempAddrArray[index].shorts[short_index];
}

/**
 * Requests a temperature be recorded by the sensor on the bus corresponding to the address
 * 
 * @param address The DAC address of the index = (address - NUM_BOARDS*2*4) temp sensor on the 1-wire bus
 * @return false if sensor is disconnected; true otherwise
 */
bool recordT(uint16_t address)
{
  uint16_t index = (address - 1 - DAC_V_LEN)/4; //Which temp sensor on the bus to choose (0 is closest to Arduino)
  return temp_sensors.requestTemperaturesByAddress(tempAddrArray[index].bytes);
}

/**
 * Gets the temperature previously recorded by the sensor on the bus corresponding to the address
 * 
 * @param address The DAC address of the (address - NUM_BOARDS*2*4)th temp sensor on the 1-wire bus
 */
uint16_t getT(uint16_t address)
{
  uint16_t index = (address - 1 - DAC_V_LEN)/4; //Which temp sensor on the bus to choose (0 is closest to Arduino)
  return (uint16_t)(temp_sensors.getTemp((uint8_t*) tempAddrArray[index].bytes) + 32768); //Convert to uint16 for transmission
}
