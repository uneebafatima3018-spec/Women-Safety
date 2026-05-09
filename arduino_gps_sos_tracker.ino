const int buttonPin = 2;
const int ledPin    = 3;
const int buzzerPin = 4;

bool alarmState = false;
unsigned long lastTrackSent = 0;
const unsigned long trackInterval = 4000;

// Siren variables
unsigned long lastSirenTime = 0;
const unsigned long sirenSpeed = 15;  // Speed of siren change
int sirenFreq = 600;
bool sirenRising = true;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  digitalWrite(ledPin, LOW);
  noTone(buzzerPin);

  Serial.begin(9600);
  Serial.println("Arduino_WOMEN_SAFETY_READY");
}

void loop() {
  // Button press with debounce
  if (digitalRead(buttonPin) == LOW) {
    delay(50);
    
    if (digitalRead(buttonPin) == LOW) {
      alarmState = !alarmState;
      
      if (alarmState) {
        Serial.println("SOS_TRIGGER");
        digitalWrite(ledPin, HIGH);
      } else {
        Serial.println("SOS_OFF");
        digitalWrite(ledPin, LOW);
        noTone(buzzerPin);  // Stop immediately
      }
      
      while (digitalRead(buttonPin) == LOW) { delay(10); }
    }
  }

  // ===== POLICE SIREN EFFECT =====
  if (alarmState) {
    unsigned long currentTime = millis();
    
    // Siren frequency sweep
    if (currentTime - lastSirenTime >= sirenSpeed) {
      lastSirenTime = currentTime;
      
      if (sirenRising) {
        sirenFreq += 30;
        if (sirenFreq >= 2500) sirenRising = false;
      } else {
        sirenFreq -= 30;
        if (sirenFreq <= 600) sirenRising = true;
      }
      
      tone(buzzerPin, sirenFreq);
    }

    // Send tracking data every 4 seconds
    if (currentTime - lastTrackSent >= trackInterval) {
      Serial.println("TRACK");
      lastTrackSent = currentTime;
    }
  }
}