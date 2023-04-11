#===============================================================================
# 01_README_rPi_ADS1115_SSD1306.txt    Version 0.9            10 Mar. 2023
#
# Setup Weather-Station on Raspberry Pi 4,  Raspian 11 (bullseye)
# native click-listener on rPi using interface-bards:
#  * Adafruit ADS11115 A/D converter at rPi
#  * SSD1306 128x164px OLED display
#  * 433MHz RF interface for Brennerstuhl swiched outlet
#
# The module currently recognizes 3, 5 or 7 clicks within a given time period
# and activates corresponding jobs.
# 3/5/7 clicks have to be activated within the code. The time window for 
# receiving the clicks can be adjusted by CML-line argument.
#===============================================================================

1. Installation
   Install current rPi OS
   Add the user "pilot" - all jobs are running under the context of user "pilot".
   Create the subfolder "weather_station" within pilots "HOME" directory - all 
   modules are located in the sub folder "weather_station"


1.1. Hardware-Installation: 
     see HowTo's for ADS1115, SSD1306 and 433RF-transmitter  boards.
	 
1.2  Cabling: Apart from Power, Ground and SDA/SCL (I2C), the choice of  
     GPIOs to use is absolutely free and must be considered accordingly 
     in the Python code of the corresponding modules.
	 
1.3. Relay
     Because a mechanical relay can jam and block the PTT button (respectively
     the radio frequency) and also the mechanical dimensions are relatively 
     large, I use a Solid State Relay (optocoupler and MOSFET). The problem 
     with SSDs is that they usually need a voltage on the load side of more than
     4 or 5 volts. My Yaesu handheld supplies only 3.3 V. The selected SSD 
     AQY211EH (4 pin DIL) is well suited for these requirements and costs only
     one dollar. 

1.4. Softwareconfiguration and Library Installation for this options,
     follow the instructions in the HowTo's in the 'Docu' folder.
	 
2.  Source of weather data
    Source of the weather data can be a local devices which provides weather-data
    via API interface. The API Interface can be reachable local (WLL) or via 
    Internet (Ecowitt).
    Modules availabel now are WeatherLink Live (WLL)and
    'ecowitt' weather station.
    Weather modules are located in the sub folder "weather"

2.1. WeatherLink Live Station
     https://weatherlink.github.io/weatherlink-live-local-api/discovery.html

2.1.1   Sources are located in the subdirectory wll:
        weather.py pulls the current weather data via API from the local (LAN)
        WLL station and generates weather.txt 
                   (weather.txt is an ascii file with numbers for TIME, WIND 
                    DIRECTION, WIND Speed, ALTIMETER, TEMPERATURE, DEWPOINT,
                    led by the key word "imperial" as the basis for the units 
                    of measure).
                    eg:
                        imperial
                        2341
                        343
                        10.0
                        30.21
                        11.5
                        3.4
        convert_weather_txt_to_wav.pl generates generate.sh
           by reading the numbers from weather.txt and assembling the 
           corresponding files of wav sniplets into a shell script.
           
        generate.sh produces weather.mp3 using 'sox' audio editor

        weather.wav is the AWOS voice file

        convert_weather_txt_to_wav.pl  and generate.sh can be superseded
        by weather_to_speach.pl which produces weather.mp3.

2.1.2 There is a crontab file that runs every 10 minutes to generate the weather
        SHELL=/bin/bash
        MAILTO=pilot@weather.local
        PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
        1,11,21,31,41,51 * * * * /home/pilot/weather_station/weather/wll/weather_loop.sh

2.1.3 weather_loop.sh
        #!/bin/sh
        /usr/bin/python3 /home/pilot/weather_station/weather/wll/weather.py
        /usr/bin/perl /home/pilot/weather_station/weather/wll/convert_weather_txt_to_mp3.pl
        sh /home/pilot/weather_station/weather/ramdisk/generate.sh

2.2. Ecowitt weather station
     Sources for realtime query of ecowitt weather station via API are located in the 
     subdirectory "ecowitt"
     ecowitt_getweather.py pulls live weather data via API from the local ecowitt sation
     via Internet (API) and generates 'weather.txt',  an ascii file with the current weather 
     basics.  'weather.txt' contain the raw numbers (AWOS) like the output of weahter.py in 
     the module 'wll' but with metric units (QNH in hPa, Temp and Dewpoint in °C).
     Therefore you have to add the CLI option -unit <imperial | metric> 

     There is also a weather_gtts.txt available, which is already adopted to the 
     culprits of Google Text to Speech (gTTS). weather_gtts.txt can be transcoded using 
     Python or Linux-Shell (CLI) libraries of gTTS.
     Output is weather.mp3. Because gTTS services are much slower than local 
     directory uplook, gtts is not used any more for transcoding weather.


2.2.1 for Google Text to Speach interface follow the HowTo in subfolder gtts

2.2.2 for ecowitt weather-station add API Keys in the API-data-File in the 
      authentication subdirectory under $HOME

2.2.3 weather_to_speech.pl (within ~/weather_station/weather) produces the audio output 
      weather.mp3. There are several language libraries available. 
      The CLI option "-lang <language>" has to be used.
      Currentliy available languages are en_us, en_uk, it and de.
      There is also a module wind_to_speech.py, which strips down the output
      to wind information only.

3. Audio output is played within the click_listener.py module by alsaplay 'aplay'or 
    the sox-player 'play', while aplay is not able to play mp3

    make sure mixer has the volume up
     sudo alsamixer

    aplay allows to speed up the output with the "tempo" qualifier. eg. "tempo 1.3" 
    or modify the volume, using CLI Options

 
4. Output AWOS information via VHF radio
   AWOS information is played by aplay or play at the audio interface of the rPi,
   which has to be connected to the MIC interface of the radio (see wiring diagram)
   Therefore, the PTT button at the radio has to be activated:

   enablePTT.py 
     aktivates the PTT button at the radio by an relay or better by a SolidStateRelay 
     in subfolder "tools".

   disablePTT.py
     deaktivates the PTT button at the radio by an relay or better by a SolidStateRelay 
     in subfolder "tools"

   Later versions of click-lister have the en-/disablePTT functions already integrated.

5.0 System Environment

5.1. all jobs are running under the context of user "pilot"; 
     see also the following 3 items.

5.2. ramdisk for logging with frequent write access:
    (ramdisk to protect the SD-Card)
     add entry to /etc/fstab:
      tmpfs /home/pilot/weather_station/ramdisk tmpfs nodev,user,nosuid,size=50M,uid=pilot,gid=pilot 0 0
     sudo mount -a or reboot

5.3. Crontab-jobs
     for (re)starting all jobs, archiving of the log files add these lines to crontab
     These have to be adopted to the local requirements. eg.:
       01 04 * * 1 pilot sudo apt-get update && sudo apt-get upgrade -y
       01 06 * * * pilot /home/pilot/weather_station/tools/reboot.sh
       01 22 * * * root /home/pilot/weather_station/tools/killweather.sh
       07 22 * * * pilot /home/pilot/weather_station/tools/archivelogs.sh


5.4. startup weather-station at boot of rPi
     add to /etc/rc.local before last exit-stmt as needed:

       sudo -H -u pilot -g pilot /home/pilot/weather_station/tools/start_weather_station.sh

    Note: "user" and "group" options with value "pilot" ar neccessary 
          for correct accesss-rights of logfiles

    !!! Better than the oldfashioned rc.local would be a systemd-Service-Unit: !!!
    copy and enable the prepared service file:
                 sudo cp ./systemd/weather_station.service /etc/systemd/system/

    follwoed by: sudo systemctl enable weather_station
                 sudo systemctl start weather_station  or reboot the system


5.5. for shutdown of rPi via push buton, add to /boot/config.txt:

      # Default: Shutdown/Startup via button on GPIO3. 
      # Since GPIO3 is used by I2C, we have to use some other, eg. 
      # GPIO19. But it works only for shutdown, not for reboot
      dtoverlay=gpio-shutdown,gpio_pin=19, active_low=1,gpio_pull=up

5.6. Performance 
      if the performance of the rPi is too weak to recognize all PTTs, try to rise the priority 
      of the program by starting it with "nice -10"
      eg:  nice -10 python3 click_listen_ada357_oled.py

6. Usage of click_listen357
6.1. to show all options for click_listen357.py, use the "-h" switch
usage: click_listen357.py [-h] [-triggerlevel TRIGGERLEVEL]
                          [-triggeradaption TRIGGERADAPTION] [-loghit] [-logweather]
                          [-trafficlight TRAFFICLIGHT] [-PTTseconds PTTSECONDS] [-message]
                          -source {WLL,ECOWITT} -unit {imperial,metric} -lang
                          {en_us,en_gb,de,it}

optional arguments:
  -h, --help            show this help message and exit
  -triggerlevel TRIGGERLEVEL
                        Optional: Triggerlevel at which a Speaker Signal should be
                        interpreted as a Click - assume 15000 should be a good starting
                        value; 15000 (1.88 V) is default.
  -triggeradaption TRIGGERADAPTION
                        Optional: allows adapiton of TRIGGERLEVEL by factor. eg. 0.6 / "1.0".
                        Or omit it to witch it completely off.
  -loghit               Optional: logs every recognized PTT hit, including signal level to
                        logfile.
  -logweather           Optional: logs the transmitted weather to logfile.
  -trafficlight TRAFFICLIGHT
                        Optional: Endurance of RED traffic light in seconds; 3 clicks
                        recognition for trafficlight is off, when not set.
  -PTTseconds PTTSECONDS
                        Optional: Timeout for n Clicks; 5 sec. default if omited
  -message              Optional: use the MESSENGER subsystem for sending messages to targts
                        like EMAIL and/or an OLED display.
  -source {WLL,ECOWITT}
                        Required: Source of weather data. Valid options are "WLL" and
                        "ECOWITT".
  -unit {imperial,metric}
                        Required: Imperial or Metric units.
  -lang {en_us,en_gb,de,it}
                        Required: Language for transcoding Weather Options are "en_us",
                        "en_gb", "de" and "it".

  

6.2. Triggerlevel
     A usable value to start is 12000 to 15000. 15000 (= 1.88 V at GAIN = 1) is the 
     default value, if no CMD line argument is set.
     Depending on the output of the speaker channel it should be customized.
     The problem with my old Icom handheld was that the level of the first
     PTT signal was much higher than the values of the following PTTs, 
     which subsequently became even lower. Another challenge is the very flat
     falling edge of the PTT signal on the Icom handheld, which occasionally
     has not yet fallen below the trigger level when the next PTT pulse is 
     already coming (see the added snapshot). To evaluate the best value for
     the Triggerlevel, I use a measuring program (clickplot.py), which I 
     is attached in the folder "tools". My Yaesu has a more stable output level.
     The built-in trigger level adaptation is not yet optimal and only covers
     the difference between the first and second PTT. Click recognition can
     still be improved.
  
6.3. Voice output of weaterh data
     Recognizing 5 clicks, local weather data are played via a connected radio.
     Weather data can be transcoded from text to speach by local media files or
     with aide of Goggle Text To Speach interface (see chapter 2).
     gTTS provides of a CLI-Inhterface and also Python libraries.
     gTTS has some peculiarities. E.g. a zero is pronounced as "oh". 
     Multi-digit numbers are pronounced together, which is unusual in 
     aviation radio. The Python program ecowitt_weather.py also provides
     weather_gtts.txt with separated digits. A pause in speech can be inserted 
     with " . ". The CMD-Line Switch "-source" chooses either the ecowitt module
     (including gTTS or local library trascoding) or the WeatherLink Live imodule 
     with "onboard" translation, using audio sniplets (media subfolder). 
     The advantage of the "onboard" translation is the independence from the Internet.

6.4 Language libraries
    New language modules for additional languages can be created very easily. 
    Either by audio recording, or by speech generator.
    The following language libraries have been generated by Google Text to Speech 
    so far: en-us, en-uk, it and de.
    For each of these language modules we created a directory within 
    ~/weather_station/media. The corresponding terms are stored in the text file 
    "numbers.txt" there.  The first column describes the variable name with which 
    the term is referenced in weather_to_speech.py or wind_to_speech.py. 
    The second column, separated by "," contains the term to be transcoded. 
    A Python program "mknumbers.py" contained in the respective language module 
    transcodes the terms into language files with the name from the first column.
    More details about gTTS at:  
    https://gtts.readthedocs.io/en/latest/module.html#languages-gtts-lang

6.5. click_messenger.py
     click_weather.py sends messages for a(OLED)display or email to 
     click_messenger.py. If the CMD-line argument "-message" is set, the 
     listener process starts the click_messenger.py process as an independent 
     background process. click_listener.py and click_messenger.py are 
     communicating via queues for interprocess communication (IPC). 
     The data required for displaying or sending e-mails is exchanged in the 
     CLASS "message" object. According to the "target" in a message, the 
     apropriate function is called. click_messenger.py and the email and 
     display modiles are positioned in the subdirectory 'messenger'.

6.6. trafficlight
     if this CMD-Line parameter is set, it switches on a remote outlet 
     via 433MHz RF for the period of seconds stated; when not present, 
     3 click recognition is off. 
     For more information consult the HowTo in the Docu folder.
