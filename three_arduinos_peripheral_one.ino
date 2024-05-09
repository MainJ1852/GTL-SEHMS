// USE WITH ARDUINO NANO EVERY
// Peripheral for LRF (corresponds to 1)

/* Naming Convention for data when sending to Pi
 *
 * 1st character: Facility #
 *   LRF = 1, VISE = 2, TTF = 3, Compressor Pit = 4
 * 
 * Then for each piece of data that's separated by spaces...
 * 
 * 1st character: Device label
 *   Thermocouples: A-J, Accelerometers: K-T, Pressure Transducers: U-Z
 * 
 * All other characters before space: Data value
 *   Two decimal places of precision
 *
 * Example: "1A78.45 B83.82 K0.13,-0.39,-9.81 U14.41"
 * LRF sent data from 2 thermocouples (motor system & motor chiller system),
 * 1 accelerometer (vacuum pump 1) w/ X,Y,Z accelerations separated by commas,
 * and 1 pressure transducer (red tank).
 */

// LIBRARIES REQUIRED FOR EVERY FACILITY
#include  <Wire.h> // I2C library
#include  <SPI.h> // SPI library
#include  <Adafruit_MAX31856.h> // MAX31856 Universal Thermocouple Amplifier library
#include  <Adafruit_LIS3DH.h> // Accelerometer library
#include  "Adafruit_MPRLS.h" // Pressure transducer library

// LRF PIN DEFINITIONS.
#define   LRF_TC_MOTOR_SYSTEM_CS_PIN           10 // TC = Thermocouple, ACC = Accelerometer, PRES = Pressure Transducer
#define   LRF_TC_MOTOR_CHILLER_SYSTEM_CS_PIN   9
#define   LRF_ACC_VAC_PUMP_1_CS_PIN            8
#define   DE_RE_PIN                            5 // Pin that toggles transmitter/receiver mode for RS-485 bus

// LRF OBJECT DECLARATIONS.
Adafruit_MAX31856  LRF_TC_MOTOR_SYSTEM = Adafruit_MAX31856(LRF_TC_MOTOR_SYSTEM_CS_PIN); // Thermocouples
Adafruit_MAX31856  LRF_TC_MOTOR_CHILLER_SYSTEM = Adafruit_MAX31856(LRF_TC_MOTOR_CHILLER_SYSTEM_CS_PIN);
Adafruit_LIS3DH    LRF_ACC_VAC_PUMP_1 = Adafruit_LIS3DH(LRF_ACC_VAC_PUMP_1_CS_PIN); // Accelerometers
Adafruit_MPRLS     LRF_PRES_RED_TANK = Adafruit_MPRLS(); // Pressure Transducers

// CONSTANTS
#define PERIPHERAL 49 // Denotes Arduino # that Pi will recognize (corresponds to 1 in ASCII)
#define PRES_HPA_TO_PSI 68.947572932 // Used to convert pressure transducer command output from hPa to psi.

// GLOBAL VARIABLES
int cycle_per_second = 0; // Used to keep track of how many times accel/pres values have been sent per second (capped at 5 for now)
float LRF_temp_motor_system = 0, LRF_temp_motor_chiller_system = 0; // LRF temperature variables
float LRF_pres_red_tank_reading = 0; // LRF pressure variables
String message = ""; // Data string sent to Raspberry Pi containing health monitoring data, sent ~5 times a second
int command_from_Pi; // Used to read RS-485 bus line (receives command prompts from Pi)

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);

  pinMode(DE_RE_PIN, OUTPUT);
  digitalWrite(DE_RE_PIN, LOW); //begin in receiving state to wait for commands from Pi

  // Turn on instrument objects so they begin communicating with Arduino
  LRF_TC_MOTOR_SYSTEM.begin();
  LRF_TC_MOTOR_SYSTEM.setConversionMode(MAX31856_CONTINUOUS);
  LRF_TC_MOTOR_CHILLER_SYSTEM.begin();
  LRF_TC_MOTOR_CHILLER_SYSTEM.setConversionMode(MAX31856_CONTINUOUS);
  LRF_ACC_VAC_PUMP_1.begin();
  LRF_PRES_RED_TANK.begin();
}

void loop() {
  // Reset message variables and increment cycle_per_second variable
  message = String(PERIPHERAL-48);
  cycle_per_second++;

  // On fifth cycle (last one per second), get thermocouple readings and append to message string
  if (cycle_per_second == 5) {
    LRF_temp_motor_system = LRF_TC_MOTOR_SYSTEM.readThermocoupleTemperature()*9/5+32;
    LRF_temp_motor_chiller_system = LRF_TC_MOTOR_CHILLER_SYSTEM.readThermocoupleTemperature()*9/5+32;
    message += "A" + String(LRF_temp_motor_system,2) + " ";
    message += "B" + String(LRF_temp_motor_chiller_system,2) + " ";

    // Reset cycle_per_second variable
    cycle_per_second = 0;
  }

  // Generate accelerometer readings
  LRF_ACC_VAC_PUMP_1.read();
  sensors_event_t LRF_ACC_VAC_PUMP_1_reading;
  LRF_ACC_VAC_PUMP_1.getEvent(&LRF_ACC_VAC_PUMP_1_reading);

  // Append accelerometer readings to message string
  message += "K" + String(LRF_ACC_VAC_PUMP_1_reading.acceleration.x,2) + ",";
  message += String(LRF_ACC_VAC_PUMP_1_reading.acceleration.y,2) + ",";
  message += String(LRF_ACC_VAC_PUMP_1_reading.acceleration.z,2) + " "; //-9.81 accounts for gravity

  // Generate pressure readings and append to message string
  LRF_pres_red_tank_reading = LRF_PRES_RED_TANK.readPressure();
  LRF_pres_red_tank_reading = LRF_pres_red_tank_reading / PRES_HPA_TO_PSI;
  message += "U" + String(LRF_pres_red_tank_reading,2);

  // Calls send_message function to send data to Pi
  Serial.println(message);
  //send_message();

  //Serial.println("Check 1");
  if (Serial1.available()) {
    //Serial.println("Check 2");
    command_from_Pi = Serial1.read(); // Get command from RS-485 bus
    Serial.println(command_from_Pi - 48);

    if (command_from_Pi == PERIPHERAL) { // Command prompts LRF for data
      digitalWrite(DE_RE_PIN, HIGH); // Set to transmitter mode
      delay(10);
      Serial1.println(message); // Send LRF data to Pi
      delay(10);
      digitalWrite(DE_RE_PIN, LOW); // Set to receiver mode
      delay(10);
      Serial.println("LRF data sent.");
    } else if (command_from_Pi == PERIPHERAL + 1) { // Command prompts VISE for data
      delay(30); // was initially 50ms
      Serial1.readStringUntil('\n'); // Clears data that VISE sends from serial buffer
    }
  }
  delay(60);
}
/*
void send_message() {
  //Serial.println("Check 1");
  if (Serial1.available()) {
    //Serial.println("Check 2");
    command_from_Pi = Serial1.read(); // Get command from RS-485 bus
    Serial.println(command_from_Pi - 48);

    if (command_from_Pi == PERIPHERAL) { // Command prompts LRF for data
      digitalWrite(DE_RE_PIN, HIGH); // Set to transmitter mode
      delay(10);
      Serial1.println(message); // Send LRF data to Pi
      delay(10);
      digitalWrite(DE_RE_PIN, LOW); // Set to receiver mode
      delay(10);
      Serial.println("LRF data sent.");
    } else if (command_from_Pi == PERIPHERAL + 1) { // Command prompts VISE for data
      delay(50); // was initially 50ms
      Serial1.readStringUntil('\n'); // Clears data that VISE sends from serial buffer
    }
  }
}*/