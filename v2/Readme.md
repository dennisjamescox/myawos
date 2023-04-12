Another optimization is the replacement of the Arduino controller by an Adafruit ADS1115 A/D converter directly on the rPi. By eliminating the Arduino, the setup is greatly simplified. In this case, the rPi detects the click signals on the radio and performs the desired activities as mentioned above. An edge detection improves the selectivity of the individual clicks. Another advance is the completely redesigned translation of text to speech within a Python module and local language libraries.
I added an OLED display and some control LEDs to the system. Also a 433 MHz transmitter and receiver to control a traffic light/flashlight (via radio-controlled switching socket), which warns the neighbors when using a dirt road at the airfield during flight operations.
The PTT button of the radio is not operated by a mechanical relay, but by a solid state relay (AQY211EH), which can no longer jam.




