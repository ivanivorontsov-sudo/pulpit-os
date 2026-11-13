/*
  Pulpit IR Bridge for ESP32
  ------------------------------------------
  Library: IRremoteESP8266 (Arduino Library Manager)
  Serial: 115200 baud, newline-delimited commands

  Wiring:
    IR LED driver input -> GPIO 4
    IR receiver OUT     -> GPIO 15
    GND                 -> common GND

  Use a transistor/MOSFET LED driver for an external IR LED.
  Do not drive a high-power IR LED directly from an ESP32 GPIO.
  The receiver should be a demodulating 38 kHz module such as TSOP38238/VS1838B.

  Commands from Pulpit:
    SEND,<frequency_hz>,<repeats>,<mark_us>,<space_us>,...
    LEARN

  Replies:
    OK,SENT
    READY,LEARN
    CAPTURE,<frequency_hz>,<timing_us>,<timing_us>,...
    ERR,<reason>
*/
#include <Arduino.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <IRrecv.h>
#include <IRutils.h>

static const uint16_t kIrSendPin = 4;
static const uint16_t kIrReceivePin = 15;
static const uint16_t kRawBufferLength = 1024;
static const uint32_t kSerialBaud = 115200;
static const uint16_t kMaxRawDuration = 65535;
static const uint16_t kMaxRepeats = 10;

IRsend irsend(kIrSendPin);
IRrecv irrecv(kIrReceivePin, kRawBufferLength, 50, true);
decode_results results;

char inputLine[12000];
size_t inputLength = 0;
bool learning = false;

void sendError(const char* reason) {
  Serial.print(F("ERR,"));
  Serial.println(reason);
}

void handleSend(char* line) {
  // Grammar: SEND,frequency_hz,repeats,timing1,timing2,...
  char* token = strtok(line, ",");
  if (!token || strcmp(token, "SEND") != 0) {
    sendError("BAD_COMMAND");
    return;
  }

  token = strtok(nullptr, ",");
  if (!token) {
    sendError("MISSING_FREQUENCY");
    return;
  }
  uint32_t frequency = strtoul(token, nullptr, 10);
  if (frequency < 20000 || frequency > 60000) {
    sendError("BAD_FREQUENCY");
    return;
  }

  token = strtok(nullptr, ",");
  if (!token) {
    sendError("MISSING_REPEATS");
    return;
  }
  uint16_t repeats = (uint16_t)strtoul(token, nullptr, 10);
  if (repeats < 1 || repeats > kMaxRepeats) {
    sendError("BAD_REPEATS");
    return;
  }

  uint16_t timings[kRawBufferLength];
  uint16_t count = 0;
  while ((token = strtok(nullptr, ",")) != nullptr) {
    if (count >= kRawBufferLength) {
      sendError("TOO_MANY_PULSES");
      return;
    }
    uint32_t duration = strtoul(token, nullptr, 10);
    if (duration == 0 || duration > kMaxRawDuration) {
      sendError("BAD_TIMING");
      return;
    }
    timings[count++] = (uint16_t)duration;
  }
  if (count < 3) {
    sendError("SIGNAL_TOO_SHORT");
    return;
  }

  learning = false;
  irrecv.disableIRIn();
  for (uint16_t i = 0; i < repeats; i++) {
    irsend.sendRaw(timings, count, (uint16_t)frequency);
    if (i + 1 < repeats) delay(35);
  }
  irrecv.enableIRIn();
  Serial.println(F("OK,SENT"));
}

void handleCommand(char* line) {
  if (strncmp(line, "SEND,", 5) == 0) {
    handleSend(line);
    return;
  }
  if (strcmp(line, "LEARN") == 0) {
    learning = true;
    irrecv.enableIRIn();
    Serial.println(F("READY,LEARN"));
    return;
  }
  if (strcmp(line, "STOP") == 0) {
    learning = false;
    irrecv.resume();
    Serial.println(F("OK,STOPPED"));
    return;
  }
  sendError("UNKNOWN_COMMAND");
}

void pollSerial() {
  while (Serial.available() > 0) {
    char value = (char)Serial.read();
    if (value == '\r') continue;
    if (value == '\n') {
      inputLine[inputLength] = '\0';
      if (inputLength > 0) handleCommand(inputLine);
      inputLength = 0;
    } else if (inputLength + 1 < sizeof(inputLine)) {
      inputLine[inputLength++] = value;
    } else {
      inputLength = 0;
      sendError("COMMAND_TOO_LONG");
    }
  }
}

void pollReceiver() {
  if (!learning) return;
  if (!irrecv.decode(&results)) return;

  const uint16_t limit = min((uint16_t)results.rawlen, kRawBufferLength);
  Serial.print(F("CAPTURE,38000"));

  // rawbuf[0] is the idle gap before the first mark, so skip it.
  for (uint16_t index = 1; index < limit; index++) {
    uint32_t duration = (uint32_t)results.rawbuf[index] * kRawTick;
    if (duration == 0) duration = 1;
    if (duration > kMaxRawDuration) duration = kMaxRawDuration;
    Serial.print(',');
    Serial.print(duration);
  }
  Serial.println();
  learning = false;
  irrecv.resume();
}

void setup() {
  Serial.begin(kSerialBaud);
  irsend.begin();
  irrecv.enableIRIn();
  Serial.println(F("PULPIT_IR_BRIDGE,1"));
}

void loop() {
  pollSerial();
  pollReceiver();
}
