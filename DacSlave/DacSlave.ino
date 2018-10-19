/**
 * @file DacSlave.ino
 * @author Austin Stover
 * @date June 2018
 * 
 * This program communicates with a computer running DacMaster.py using the Modbus 
 * RS485 protocol to manage AD5504 DACs for the APT experiment CERN prototype
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
#include <ModbusSlave.h>

const int SLAVE_ID = 0; ///< This specifies which Arduino to which the master will talk
const int BAUD_RATE = 9600;

const int TX_PIN = 2; ///< This is the DE/RE pin for the Serial to RS485 converter
const int LDAC_PIN = 47;a ///< This pin is pulsed to move data from input to DAC register
const int CLR_PIN = 45;

const uint8_t NUM_SIPM_CHANS = 1;
const uint8_t NUM_BOARDS = 1; ///< The number of boards per SiPM channel
    
/**
 * @brief PIN_ARRAY[] relates the DAC channel chip select outputs to specific Arduino pins.
 * 
 * There is 1 pin per DAC and 2 DACs per board, NUM_BOARDS per SiPM channel, and
 * NUM_SIPM_CHANS SiPM channels overall. The first 2 pins in the array therefore denote 
 * DAC pins (chip selects) 0 and 1 on board 0. The next two pins are 0 and 1 on board 1,
 * etc. as illustrated below, where n=NUM_BOARDS. The element index is related to these 
 * parameters by the following equation:
 * vIndex = address = NUM_BOARDS*4*2*sipmChan + 4*2*boardNum + 4*dacNum + dacChan
*/
const uint8_t PIN_ARRAY_LEN = NUM_SIPM_CHANS*NUM_BOARDS*2;
const uint8_t PIN_ARRAY[PIN_ARRAY_LEN] = {44,46};
// Element index:                         0  1  2  3  4  5 ... 
// DAC Number:                            0  1  0  1  0  1 ... 0  1  0  1
// Board Number:                          0     1     2    ... n     n+1
// SiPM Channel:                          0                    1

const uint16_t CONTROL_ARRAY_LEN = NUM_SIPM_CHANS*NUM_BOARDS*2;

/**
 * @brief controlArray[] elements are numbered the same way as PIN_ARRAY[] elements
 * 
 * controlArray[i] denotes the same DAC channel as PIN_ARRAY[i]. The element index is
 * related to its parameters by the following equation (using integer division):
 * cIndex = address / 4 = NUM_BOARDS*2*sipmChan + 2*boardNum + dacNum
 */
uint16_t controlArray[CONTROL_ARRAY_LEN]; //Saves the states of the control registers
    
const SPISettings spiSet{9000000, MSBFIRST, SPI_MODE0};


const uint16_t DAC_V_LEN = NUM_SIPM_CHANS*NUM_BOARDS*2*4;

/**
 * @brief dacV[] holds the voltage for each DAC channel
 * 
 * There are 4 times as many entries in this array as there are in PIN_ARRAY[] or 
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
// SiPM Channel:             0                         ...

//Connect the RS485 communication line to the below Serial port
Modbus slave(Serial1, SLAVE_ID, TX_PIN); 

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
  for(int j = 0; j < PIN_ARRAY_LEN; j++)
  { //Initialize chip select pins
    pinMode(PIN_ARRAY[j], OUTPUT);
    digitalWrite(PIN_ARRAY[j], HIGH);
  }
  
  SPI.begin();

  //Callback handler function declarations
  slave.cbVector[CB_READ_COILS] = readCoil;
  slave.cbVector[CB_WRITE_COILS] = writeCoil;
  slave.cbVector[CB_READ_REGISTERS] = readReg;
  slave.cbVector[CB_WRITE_REGISTERS] = writeReg;
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
  {
    if(address < DAC_V_LEN)
    {
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
  {
    if(address < DAC_V_LEN)
    {
      slave.writeRegisterToBuffer(0, getV(address));
      return STATUS_OK;
    }
    else
      return STATUS_ILLEGAL_DATA_ADDRESS;
  }
  else if(fc == FC_READ_INPUT_REGISTERS)
  { //Reading an input register reads the approximate voltage in a DAC input register
    if(address < DAC_V_LEN)
    {
      slave.writeRegisterToBuffer(0, readV(address));
    }
    else
      STATUS_ILLEGAL_DATA_ADDRESS;
  }
  else
    return STATUS_ILLEGAL_FUNCTION;
}

/**
 * Callback function for writing single bits to turn on/off DAC channel analog outputs
 */
uint8_t writeCoil(uint8_t fc, uint16_t address, uint16_t length)
{
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
{
  if(fc == FC_READ_COILS)
  {
    if(address < DAC_V_LEN)
    {
      slave.writeCoilToBuffer(0, getPower(address));
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
  uint8_t dacPin = PIN_ARRAY[address / 4];

  //Creates the input register byte
  uint16_t updateVoltageWord = (newV % 4096) + (((address+1) % 4) << 12);
  
  SPI.beginTransaction(spiSet);
  
  digitalWrite(dacPin, LOW); //Hold SYNC low on this DAC to update input register
  delayMicroseconds(1);
  SPI.transfer16(updateVoltageWord);
  delayMicroseconds(1);
  digitalWrite(dacPin, HIGH);
  
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
  uint16_t dacPin = PIN_ARRAY[address / 4];

  //This byte picks out the power-up/down bit for the DAC channel
  uint16_t bitLoc = _BV(address % 4 + 2);

  //If you want to power up the channel, set the bit to 1; else 0
  powWord = powerOn ? powWord | bitLoc : powWord & ~bitLoc;
  //Now save the control register value
  controlArray[address / 4] = powWord;
  
  SPI.beginTransaction(spiSet);
  
  digitalWrite(dacPin, LOW);
  delayMicroseconds(1);
  SPI.transfer16(powWord);
  delayMicroseconds(1);
  digitalWrite(dacPin, HIGH);
  
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
 * NOTE: This may not return the correct value from the input register, since the SPI protocol
 *  used by the Arduino and Dac differ. Thus this method should only be used to check that a
 *  value has been loaded into the input register.
 *  @param address The DAC channel address
 *  @return The raw voltage read from the DAC channel's input register
 */
uint16_t readV(uint16_t address)
{
  uint8_t dacPin = PIN_ARRAY[address / 4];
  uint16_t readVWord = 0b1000000000000000 + (((address+1) % 4) << 12);
  
  SPI.beginTransaction(spiSet);
  
  digitalWrite(dacPin, LOW);
  delayMicroseconds(1);
  uint16_t vRead = (SPI.transfer16(readVWord) << 1) % 4096;
  delayMicroseconds(1);
  digitalWrite(dacPin, HIGH);
  
  SPI.endTransaction();
  
  return vRead;
}
