// USE WITH BLUE ARDUINO LEONARDO
// Peripheral for VISE (corresponds to 2)

#define PERIPHERAL 50 // ASCII for 2
#define DE_RE_PIN 5 // Pin that toggles transmitter/receiver mode

int command_from_Pi;

void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);

  pinMode(DE_RE_PIN, OUTPUT);
  digitalWrite(DE_RE_PIN, LOW); //begin in receiving state to wait for commands from Pi
}

void loop() {
  delay(10); //Simulation speed for gathering data from sensors
  if (Serial1.available()) {
    command_from_Pi = Serial1.read(); // Get data from RS-485 bus
    Serial.println(command_from_Pi - 48);

    if (command_from_Pi == PERIPHERAL) { // Command prompts VISE for data
      digitalWrite(DE_RE_PIN, HIGH); // Set to transmitter mode
      delay(10);
      Serial1.println("2A82.45 B73.38 K0.24,-0.14,0.08 U14.43");
      delay(10);
      digitalWrite(DE_RE_PIN, LOW); // Set to receiver mode
      delay(10);
      Serial.println("VISE data sent.");
    } else if (command_from_Pi == PERIPHERAL - 1) { // Command prompts LRF for data
      delay(30);
      Serial1.readStringUntil('\n'); // Clears data that LRF sends from serial buffer
    }
  }
  delay(60);
}