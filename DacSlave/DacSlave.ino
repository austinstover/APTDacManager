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

const int SLAVE_ID = 0; ///< This specifies to which Arduino the master will talk
const int BAUD_RATE = 9600;

const int TX_PIN = 2; ///< This is the DE/RE pin for the Serial to RS485 converter
const int LDAC_PIN = 47; ///< This pin is pulsed to move data from input to DAC register
const int CLR_PIN = 45;

const int ENABLE_PIN = 46; ///< This pin enables the decoder. It is active low.

    
/**
 * @brief PIN_ARRAY[] relates the DAC channel chip select outputs to specific Arduino pins.
 * 
 * There are 7 output bits from the Arduino to the chip select decoder, which are on the
 * pins in this list.
*/
const uint8_t DAC_ADDR_LEN = 7;
const uint8_t PIN_ARRAY[DAC_ADDR_LEN] = {38,39,40,41,42,43,44}; //Decoder pins for addressing DACs
// Bit:                                   0  1  2  3  4  5  6  (2^7 addresses)

const uint16_t CONTROL_ARRAY_LEN = pow(2,DAC_ADDR_LEN);

/**
 * @brief controlArray[] elements are numbered the same way as PIN_ARRAY[] elements
 * 
 * controlArray[i] denotes the same DAC channel as PIN_ARRAY[i]. The element index is
 * related to its parameters by the following equation (using integer division):
 * cIndex = address / 4 = NUM_BOARDS*2*sipmChan + 2*boardNum + dacNum
 */
uint16_t controlArray[CONTROL_ARRAY_LEN]; //Saves the states of the control registers
    
const SPISettings spiSet{9000000, MSBFIRST, SPI_MODE0};

const uint16_t DAC_V_LEN = 4*pow(2,DAC_ADDR_LEN);

/**
 * @brief dacV[] holds the voltage for each DAC channel
 * 
 * There are 4 times as many entries in this array as there are in PIN_ARRAY[] or 
 * controlArray[], since there are 4 channels per DAC. To get the controlArray
 * element from the address, just integer divide by 4.
*/
// * 
// * There are therefore 4 elements
// * per DAC number, as illustrated. To get the controlArray element from the dacV
// * element, just integer divide by 4. The DAC channel can also be determined from the
// * dacV element by performing modulo 4 on the element #.
// */
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
//  Serial.begin(115200); 

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

  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); //Enable the decoder
  
  for(int i = 0; i < CONTROL_ARRAY_LEN; i++)
  { //Initialize control register commands to all Dacs off
    controlArray[i] = 0b0111000000000000;
  }
  
  //Initialize decoder pins
  for(int j = 0; j < DAC_ADDR_LEN; j++)
  { 
    pinMode(PIN_ARRAY[j], OUTPUT);
    digitalWrite(PIN_ARRAY[j], LOW);
  }
  
  //Initialize chip selects
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH); //Start with all CS disabled
  
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
//  Serial.print("1. "); Serial.print(address);
//  Serial.print("\t2. "); Serial.print(address /4);
//  Serial.print("\t3. "); Serial.print(dacPin);
//  Serial.print("\t4. "); Serial.print(address % 4,BIN);
//  Serial.print("\t5. "); Serial.print((address+1) % 4,BIN);
//  Serial.print("\t6. "); Serial.print((address % 4)+1,BIN);
//  Serial.print("\t7. "); Serial.print(newV % 4096,BIN);
  //Creates the input register byte
  uint16_t updateVoltageWord = (newV % 4096) + (((address % 4)+1) << 12);
//  Serial.print("\t8. "); Serial.println(updateVoltageWord, BIN);
  SPI.beginTransaction(spiSet);
  
  startSelect(address); //Start a chip select
  SPI.transfer16(updateVoltageWord);
  endSelect();
  
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

  //This byte picks out the power-up/down bit for the DAC channel
  uint16_t bitLoc = _BV(address % 4 + 2);

  //If you want to power up the channel, set the bit to 1; else 0
  powWord = powerOn ? powWord | bitLoc : powWord & ~bitLoc;
  
  //Now save the control register value
  controlArray[address / 4] = powWord;
  
  SPI.beginTransaction(spiSet);
  
  startSelect(address);
  SPI.transfer16(powWord);
  endSelect();
  
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
  uint16_t readVWord = 0b1000000000000000 + (((address % 4) + 1) << 12);
//  Serial.print("\t9. "); Serial.println(readVWord, BIN);

  SPI.beginTransaction(spiSet);
  
  startSelect(address);
  uint16_t vRead = (SPI.transfer16(readVWord) << 1) % 4096; //Leftshift one to correct for reading on wrong side of clk cycle
  endSelect();
  
  SPI.endTransaction();
//  Serial.print("\t10. "); Serial.println(vRead, BIN);
  return vRead;
}

/**
 * Perform a chip select on the desired DAC. You can perform SPI transfers directly after this, and should start the SPI transactions before.
 */
void startSelect(uint16_t address)
{
  uint16_t dac_addr = address/4;
  for(uint8_t i=0; i<DAC_ADDR_LEN; i++)
  {
    digitalWrite(PIN_ARRAY[i], bitRead(dac_addr, i)); //Turns on/off decoder pins that are a binary 1/0 in the address.
  }
  delayMicroseconds(1);
}

/**
 * Finish a chip select on the desired DAC. You should perform any SPI transfers directly before this and end the SPI transaction afterwards.
 */
void endSelect()
{
  delayMicroseconds(1);
  digitalWrite(ENABLE_PIN, HIGH);
}
