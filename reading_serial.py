import serial
ser=serial.Serial('/dev/ttyAMA0',19200)
readedText = ser.readline()
print(readedText)
ser.close()

