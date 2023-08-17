#include <Wire.h>
#include <SPI.h>
#include <Adafruit_MAX31856.h>
#include <Adafruit_LIS3DH.h>
#include "Adafruit_MPRLS.h"

#define RESET_PIN  -1  // These two pins are for the pressure sensor, not using these pins but needed in object declaration
#define EOC_PIN    -1 
#define PRES_CONV 68.947572932 // Constant for converting from hPa to psi

Adafruit_MAX31856 maxthermo1 = Adafruit_MAX31856(9);
Adafruit_MAX31856 maxthermo2 = Adafruit_MAX31856(10);
Adafruit_LIS3DH accel = Adafruit_LIS3DH(8);
Adafruit_MPRLS pres = Adafruit_MPRLS(RESET_PIN, EOC_PIN);

int count = 0;
float temp1 = 0, temp2 = 0, pres_hPa = 0, pres_PSI = 0;
String message = "";

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  
  accel.begin();
  maxthermo1.begin();
  maxthermo2.begin();
  pres.begin();
}

void loop() {
  accel.read();
  sensors_event_t event;
  accel.getEvent(&event);

  message += "X" + String(event.acceleration.x,2) + " ";
  message += "Y" + String(event.acceleration.y,2) + " ";
  message += "Z" + String(event.acceleration.z,2) + " ";

  pres_hPa = pres.readPressure();
  pres_PSI = pres_hPa / PRES_CONV;
  message += "?" + String(pres_PSI,2);

  if (count % 5 == 0) { //takes about 550 milliseconds for this loop
    count = 0;
    
    temp1 = maxthermo1.readThermocoupleTemperature()*9/5+32;
    temp2 = maxthermo2.readThermocoupleTemperature()*9/5+32;
    message += " A" + String(temp1,2) + " ";
    message += "B" + String(temp2,2);

    Serial.println(message);
    Serial1.println(message);
  } 
  else { //takes about 166 milliseconds
    delay(159);
    
    Serial.println(message);
    Serial1.println(message);
  }
  
  message = "";
  count++;
}