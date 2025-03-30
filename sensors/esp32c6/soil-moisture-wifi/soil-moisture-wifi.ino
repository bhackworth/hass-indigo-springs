#include <ArduinoJson.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <NetworkClient.h>
#include <HTTPClient.h>
#include <math.h>

#include "../../../../../../../../../src/hackware/sensors/include/smooth.hpp"
#include "arduino_secrets.h"

#define FW_VERSION "0.1.6"

// WiFi, HTTP settings
#ifndef WL_MAC_ADDR_LENGTH
#define WL_MAC_ADDR_LENGTH 6
#endif
uint8_t macAddress[WL_MAC_ADDR_LENGTH];

typedef struct {
  char *host;
  uint16_t port;
} server_t;

server_t servers[] = {
  { "192.168.1.11", 8200 },
  { "192.168.1.61", 8234 },
  { "homeassistant", 8234 }
};

#define MILLI (1000)
#define MICRO (1000 * 1000)

const int secondsToSleep = 5 * 60;
const uint32_t smoothingWindow = 3;

// Soil moisture settings
const int dhtPin = 0;
const int moisturePin = 1;
const int batteryPin = 2;
char sensorName[7];

// These calibrated with 3.3v on ESP32-C6
const int superWet = 1048;
const int superDry = 2048;

const int batteryFull = 4200; // millivolts, according to spec
const int batteryEmpty = 3200; // millivots

#ifdef LED_BUILTIN
const int ledPin = LED_BUILTIN;
#endif
const int ledON = LOW;
const int ledOFF = HIGH;

int needToCalibrate = 0;

typedef struct {
  Smooth<int, smoothingWindow> voltage;
  Smooth<float, smoothingWindow> moisture;
  Smooth<float, smoothingWindow> temperature;
  Smooth<float, smoothingWindow> humidity;
  Smooth<float, smoothingWindow> battery;
} sample_t;

sample_t samples;
DHT dht(dhtPin, DHT11);

void setup() {
  Serial.begin(19200);

  dht.begin();
  pinMode(moisturePin, INPUT);
  pinMode(batteryPin, INPUT);

  #ifdef LED_BUILTIN
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, ledOFF);
  #endif

  Serial.printf("Connecting to %s\n", SECRET_SSID);
  int status = WiFi.begin(SECRET_SSID, SECRET_PASS);
  while (WiFi.waitForConnectResult() != WL_CONNECTED) {
    delay(100);
  }

  WiFi.macAddress(macAddress);
  snprintf(sensorName, sizeof(sensorName)/sizeof(char),
      "%02X%02X%02X", macAddress[3], macAddress[4], macAddress[5]);
  printWifiStatus();
}
float roundoff(float val) {
  return floor((val * 10.0) + 0.5) / 10.0;
}
void send_sample(sample_t * samples) {
  WiFiClient net;
  HTTPClient client;

  for (int idx = 0; idx < (sizeof(servers)/sizeof(servers[0])); idx++) {
      server_t server = servers[idx];
      Serial.printf("\nConnecting to %s:%d\n", server.host, server.port);
      if (client.begin(net, server.host, server.port, "/api/samples")) {
        JsonDocument json;
        json["voltage"] = samples->voltage.get();
        json["moisture"] = roundoff(samples->moisture.get());
        json["temperature"] = roundoff(samples->temperature.get());
        json["humidity"] = roundoff(samples->humidity.get());
        json["battery"] = roundoff(samples->battery.get());
        json["sensor"] = sensorName;
        json["sn"] = sensorName;
        json["fw-version"] = FW_VERSION;

        String data;
        serializeJson(json, data);

        Serial.print("Sending ");
        Serial.println(data);

        client.addHeader("Host", server.host);
        client.addHeader("Content-type", "text/json");
        client.addHeader("Connection", "close");

        int responseCode = client.POST(data);
        Serial.printf("%d: ", responseCode);
        Serial.println(client.getString());
      } else {
        Serial.printf("couldn't connect to %s:%d\n", server.host, server.port);
      }
  }
}

void sample_and_send() {

#ifdef LED_BUILTIN
  digitalWrite(ledPin, ledON);
#endif

  int moistureVolts = analogReadMilliVolts(moisturePin);
  float moisture = map(moistureVolts, superWet, superDry, 1000, 0) / 10.0;
  moisture = constrain(moisture, 0.0F, 100.0F);
  moisture = floor((moisture * 10.0) + .5)/ 10.0; // truncate to one decimal place
  // samples.voltage.add(moistureVolts);
  samples.moisture.add(moisture);

  samples.temperature.add(dht.readTemperature());
  samples.humidity.add(dht.readHumidity());

  int batteryMilliVolts = analogReadMilliVolts(batteryPin);
  batteryMilliVolts *= 2; // battery divider circuit
  int batteryPercent = map(batteryMilliVolts, batteryEmpty, batteryFull, 0, 100);
  batteryPercent = constrain(batteryPercent, 0, 100);
  samples.battery.add(batteryPercent);
  samples.voltage.add(batteryMilliVolts);
  send_sample(&samples);

#ifdef LED_BUILTIN
  digitalWrite(ledPin, ledOFF);
#endif
}

void loop() {
  sample_and_send();
  delay(secondsToSleep * MILLI);
}

void printWifiStatus() {
  Serial.printf("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.printf("Signal strength: %l dBm\n", WiFi.RSSI());
  Serial.printf("Sensor: %s\n", sensorName);
}
