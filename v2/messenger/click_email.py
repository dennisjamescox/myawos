# Import smtplib and ssl  for the actual sending function
import smtplib
import ssl
# Import the email modules we'll need
from email.message import EmailMessage
import os
import subprocess
import socket

class nachricht:
   def __init__(self, target, address, subject, text, priority):
      self.target = target
      self.address = address
      self.subject = subject
      self.text = text
      self.priority = priority

def send_email(mail):

    HOME = os.environ['HOME']
    accuntdata = HOME + "/.weather_station_authentication/account.txt"

    HOSTNAME = socket.gethostname()

    # SMTP data file, line by line:
    # <smtp-server>
    # <smtp-server port>
    # <account for login>
    # <password for login>

    f=open(accuntdata, "r")
    lines=f.readlines()
    for i in range(len(lines)):
       lines[i] = lines[i].strip()
    f.close()

    smtp_server = lines[0]
    smtp_port = lines[1]
    smtp_login = lines[2]
    smtp_passwd = lines[3]

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_login, smtp_passwd)

    msg = EmailMessage()
    msg.set_content(mail.text)
    msg['Subject'] = mail.subject
    msg['From'] = HOSTNAME + ' rPi click_listener'
    msg['To'] = mail.address

    server.send_message(msg)

    server.close()

