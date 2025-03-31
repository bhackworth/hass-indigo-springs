# Indigo Springs

Custom software for homemade soil moisture sensors and the corresponding Home Assistant integration.

## Soil moisture probe

The PROBE-01 model is an ESP32-based microcontroller with a temperature sensor and battery
monitoring circuit. It creates several sensors:

* Air temperature
* Air relative humidity
* Soil moisture level
* Battery level

The probe wakes up periodically to post new samples to an HTTP server running on the 
Home Assistant system at port 8234.
