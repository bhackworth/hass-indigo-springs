# BOARD = esp32:esp32:XIAO_ESP32C6
BOARD = esp32:esp32:XIAO_ESP32C3
PORT = usbmodem14601
ARDUINO_OPTS = --build-path ./.build --fqbn $(BOARD)

.PHONY: all compile upload lint

all: compile upload serial

lint:
	cpplint --extensions=ino --filter=-legal/copyright *.ino
	
compile:
	arduino-cli compile $(ARDUINO_OPTS) ./

upload:
	arduino-cli upload -p /dev/cu.$(PORT) $(ARDUINO_OPTS) ./

serial:
	@echo "Kill with Ctrl-A + k"
	screen -O /dev/tty.$(PORT) 19200
