
#include <math.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <NetworkClient.h>
#include <HTTPClient.h>
#include <esp_sleep.h>
#include <esp_wifi.h>

#include <cstdio>

#include "smooth.hpp"
#include "arduino_secrets.h"

#define SW_VERSION "1.4.2"

// Hardware versions:
// 1.0 - 5x7cm PCB, ESP32-C6, DHT11 on pin A0, soil moisture sensor on A1
// 1.1 - Add battery voltage divider circuit on A2
// 1.2 - Swap DHT11 for DHT22, ESP32-C3 for -C6
// 1.3 - Add solar charger with divider circuit on A1; 47k resistor from +, 22k to GND
#define HW_VERSION "1.3.0"
#define MEASURE_SOLAR

// WiFi, HTTP settings
#ifndef WL_MAC_ADDR_LENGTH
#define WL_MAC_ADDR_LENGTH 6
#endif
uint8_t macAddress[WL_MAC_ADDR_LENGTH];

typedef struct {
    char *host;
    uint16_t port;
    char *token;
} server_t;

server_t servers[] = {
    { "192.168.1.11", 8200, NULL }, // tracing server
    { "192.168.1.61", 8123, TOKEN_DEV }, // homeassistant-dev
    { "homeassistant.local", 8123, TOKEN_PROD }, // homeassistant-prod
};

#define DEBUG_PRINTLN(x) Serial.println(x)
#define DEBUG_PRINTF(x, ...) Serial.printf(x, __VA_ARGS__)

#define MILLI (1000)
#define MICRO (1000 * 1000)

int secondsToSleep = 5 * 60;

// To reduce the jumpiness of readings, report a moving average
// over a certain number of samples.
const uint32_t smoothingWindow = 6;

// Must use pin aliases ("A0" vs "0") because the integer
// mappings are different between ESP32-C3 and ESP32-C6
const int dhtPin = A0;

// There are only 3 analog pins. Measure soil moisture
// or solar voltage, but not both.
#ifdef MEASURE_SOIL
const int moisturePin = A1;
#ifdef MEASURE_SOLOR
#error You can't measure soil and solar on the same system.
#endif
#endif
#ifdef MEASURE_SOLAR
const int solarPin = A1;
#endif

const int batteryPin = A2;
char sensorName[7];

// Soil mosture sensor calibrated with 3.3v on ESP32-C6
const int superWet = 1048;
const int superDry = 2048;

const int batteryFull = 4200;   // millivolts, according to spec
const int batteryEmpty = 3200;  // millivots

#ifdef LED_BUILTIN
const int ledPin = LED_BUILTIN;
#endif
const int ledON = LOW;
const int ledOFF = HIGH;

typedef struct {
    Smooth<int, smoothingWindow> batteryVoltage; // in millivolts
    Smooth<float, smoothingWindow * 4> batteryPercent;  // battery charge percent, 0-100;
                                                 // smooth over a much longer window because
                                                 // it doesn't change rapidly
#ifdef MEASURE_SOIL
    Smooth<float, smoothingWindow> moisture;     // soil moisture, in percent, 0-100
#endif
    Smooth<float, smoothingWindow> temperature;  // in •C
    Smooth<float, smoothingWindow> humidity;     // air relative humidity, in percent, 0-100
#ifdef MEASURE_SOLAR
    Smooth<int, smoothingWindow> solarVoltage;   // in millivolts
#endif
} sample_t;

RTC_DATA_ATTR sample_t samples;
DHT dht(dhtPin, DHT22);

void waitForSerial(int millisec = 1500) {
    Serial.begin(19200);
    int waitUntil = millis() + millisec;
    while (millis() < waitUntil) {
        if (Serial.available()) {
            Serial.println("Serial monitor detected; shortening the refresh interval.");
            secondsToSleep /= 30;
            break;
        }
    }
}
void setup() {
    waitForSerial();
}

void initializePins() {
    // pinMode(dhtPin, INPUT_PULLUP);
#ifdef MEASURE_SOIL
    pinMode(moisturePin, INPUT);
#endif
#ifdef MEASURE_SOLAR
    pinMode(solarPin, INPUT);
#endif
    pinMode(batteryPin, INPUT);

#ifdef LED_BUILTIN
    pinMode(ledPin, OUTPUT);
    digitalWrite(ledPin, ledOFF);
#endif

    dht.begin();
}
void goToSleep() {
    uint64_t sleepTime = static_cast<uint64_t>(secondsToSleep * MICRO);
    int espOk = esp_sleep_enable_timer_wakeup(sleepTime);
    if (ESP_OK != espOk) {
        Serial.printf("Error enabling wakeup timer: %d\r\n", espOk);
    }

    DEBUG_PRINTF("Sleeping for %d secs\r\n", secondsToSleep);
    Serial.flush();
    delay(500);
    WiFi.disconnect(true, true);
    esp_deep_sleep_start();

    // This code should never be reached after deep sleep
    DEBUG_PRINTF("Awake from sleep; code %d\r\n", espOk);
    printWakeupReason();
}

// Round to one decimal place. Ex: 9.87 -> 9.9
float roundOff(float val) {
    return floor((val * 10.0) + 0.5) / 10.0;
}
void sendSample(sample_t * samples) {
    WiFiClient net;

    DEBUG_PRINTLN("Sending sample");
    Serial.printf("Connecting to Wi-Fi network %s\r\n", SECRET_SSID);

    int maxSecondsForWiFi = 5;

    int status = WiFi.begin(SECRET_SSID, SECRET_PASS);
    status = WiFi.waitForConnectResult(maxSecondsForWiFi * MILLI);
    if (status != WL_CONNECTED) {
        Serial.printf("Couldn't connect to Wi-Fi: %d\r\n", status);
        return;
    }
    WiFi.macAddress(macAddress);
    snprintf(sensorName, sizeof(sensorName)/sizeof(char),
        "%02X%02X%02X", macAddress[3], macAddress[4], macAddress[5]);

    printWifiStatus();
    JsonDocument json;

    json["rssi"] = WiFi.RSSI();
    json["voltage"] = samples->batteryVoltage.get();
#ifdef MEASURE_SOIL
    json["moisture"] = roundOff(samples->moisture.get());
#endif
    json["temperature"] = roundOff(samples->temperature.get());
    json["humidity"] = roundOff(samples->humidity.get());
    json["battery"] = roundOff(samples->batteryPercent.get());
#ifdef MEASURE_SOLAR
    json["solar"] = samples->solarVoltage.get();
#endif
    json["sensor"] = sensorName;
    json["sn"] = sensorName;
    json["sw"] = SW_VERSION;
    json["hw"] = HW_VERSION;

    String data;
    serializeJson(json, data);
    Serial.print("Sending ");
    Serial.println(data);

    for (int idx = 0; idx < (sizeof(servers)/sizeof(servers[0])); idx++) {
        server_t server = servers[idx];
        HTTPClient client;

        Serial.printf("Connecting to %s:%d\r\n", server.host, server.port);
        if (client.begin(net, server.host, server.port, "/api/indigo-springs/samples")) {
            client.addHeader("Host", server.host);
            client.addHeader("Content-type", "application/json");
            if (server.token != NULL) {
                char token[512];
                snprintf(token, sizeof(token), "Bearer %s", server.token);
                client.addHeader("Authorization", token);
            }
            client.addHeader("Connection", "close");

            int responseCode = client.POST(data);
            Serial.printf("Response: %d ", responseCode);
            Serial.println(client.getString());
        } else {
            Serial.printf("couldn't connect to %s:%d\r\n",
                server.host, server.port);
        }
    }
}

void sampleAndSend() {
    Serial.println("Sampling");
    initializePins();
#ifdef LED_BUILTIN
    digitalWrite(ledPin, ledON);
#endif

#ifdef MEASURE_SOIL
    int moistureVolts = analogReadMilliVolts(moisturePin);
    float moisture = map(moistureVolts, superWet, superDry, 1000, 0) / 10.0;
    moisture = constrain(moisture, 0.0F, 100.0F);
    // truncate to one decimal place
    moisture = floor((moisture * 10.0) + .5)/ 10.0;
    // samples.voltage.add(moistureVolts);
    samples.moisture.add(moisture);
#endif

    if (true) {
        dht.read();
        Serial.printf("Temperature reading: %.1f\r\n", dht.readTemperature());
        Serial.printf("Air humidity reading: %.1f\r\n", dht.readHumidity());
    }
    samples.temperature.add(dht.readTemperature());
    samples.humidity.add(dht.readHumidity());

    int batteryMilliVolts = analogReadMilliVolts(batteryPin);
    batteryMilliVolts *= 2;  // battery divider circuit
    int batteryPercent = map(batteryMilliVolts,
        batteryEmpty, batteryFull, 0, 100);
    batteryPercent = constrain(batteryPercent, 0, 100);
    samples.batteryPercent.add(batteryPercent);
    samples.batteryVoltage.add(batteryMilliVolts);

#ifdef MEASURE_SOLAR
    /*
     * The panel I'm using can output up to 6v, so we use
     * a divider circuit with 22K and 47K resistors to bring
     * the voltage down to a range that the ESP32 can measure.
     *
     *  Ohm's law: vactual = (measured * (r1 + r2)) / r2
     */
    int solarMilliVolts = analogReadMilliVolts(solarPin);
    solarMilliVolts = (solarMilliVolts * (47000 + 22000)) / 22000; // divider circuit
    samples.solarVoltage.add(solarMilliVolts);
#endif

    sendSample(&samples);

#ifdef LED_BUILTIN
    digitalWrite(ledPin, ledOFF);
#endif
}

void loop() {
    sampleAndSend();
    goToSleep();
}

void printWifiStatus() {
    Serial.printf("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.printf("Sensor: %s\r\n", sensorName);
}

void printWakeupReason() {
    esp_sleep_wakeup_cause_t wakeup_reason;

    wakeup_reason = esp_sleep_get_wakeup_cause();

    switch (wakeup_reason) {
        case ESP_SLEEP_WAKEUP_EXT0:
            Serial.println("Wakeup due to RTC_IO");
            break;
        case ESP_SLEEP_WAKEUP_EXT1:
            Serial.println("Wakeup due to RTC_CNTL");
            break;
        case ESP_SLEEP_WAKEUP_TIMER:
            Serial.println("Wakeup due to timer");
            break;
        case ESP_SLEEP_WAKEUP_TOUCHPAD:
            Serial.println("Wakeup due to touchpad");
            break;
        case ESP_SLEEP_WAKEUP_ULP:
            Serial.println("Wakeup due to ULP program");
            break;
        default:
            Serial.printf("Wakeup was not caused by deep sleep: %d\r\n",
                wakeup_reason);
            break;
    }
}
