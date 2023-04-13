Another optimization is the replacement of the Arduino controller by an Adafruit ADS1115 A/D converter directly on the rPi. By eliminating the Arduino, the setup is greatly simplified. 
In this setup, the rPi detects the click signals on the radio and performs the desired activities as mentioned above. 
An edge detection improves the selectivity of the individual clicks. Another advance is the completely redesigned translation of text to speech a Python module and local language libraries. 
The messaging module sends information and messages to an optional OLED display or to an email recipient. Different LEDs inform about the current status. Added a 433 MHz transmitter and receiver to control a traffic light/flashlight (via radio-controlled switching socket) that warns residents when using a dirt road at the site during flight operations.
The PTT button of the radio is not operated by a mechanical relay, but by a Solid State Relay (AQY211EH), which can no longer jam.




