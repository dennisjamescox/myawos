Another optimization is the replacement of the Arduino controller by an Adafruit ADS1115 A/D converter directly on the rPi. By eliminating the Arduino, the setup is greatly simplified. 
In this setup, the rPi detects the click signals on the radio and performs the desired activities as mentioned above. 
An edge detection improves the selectivity of the individual clicks. 
Another advance is the completely redesigned translation of text to speech within a Python module using local language libraries. 
The language libraries can be customized very easily via the respective base file (numbers.txt) and translated into language snippets with the help of gTTS (mknumbers.py). The language modules are stored under the "media" folder 
The speed of the pronunciation can be controlled by the parameter "tempo" within the click_listener module. The weather module can now optionally output metric or imperial units.
The messaging module sends information and messages to an optional OLED display or to an email recipient. It is optionally (CMD line parameter) started as a subprocess and receives the forwarding information via a queue from click_listener. 
Different LEDs inform about the current status. 
In my setup, a 433 MHz transmitter (and receiver) control a traffic light/flashlight (via radio-controlled switching socket) that warns residents when using a dirt road at the site during flight operations.
The PTT button of the radio is not operated by a mechanical relay, but by a Solid State Relay (AQY211EH), which can no longer jam.
This directory (v2) contains the sources for the ADS1115 and rPi based AWOS system. For a better overview, the individual modules are stored in different subfolders, starting in the working directory "weather_station". 
Extensive documentation and HowTo's are stored in the directory "Docu".