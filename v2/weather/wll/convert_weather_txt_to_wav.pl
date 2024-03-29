#!/usr/bin/perl
use POSIX;

# open the weather text file
open(WEATHER,"/home/pilot/weather_station/ramdisk/weather.txt") or die "Could not open weather.txt, $!";

# open the generate file
open(GENERATE,">/home/pilot/weather_station/ramdisk/generate.sh") or die "Could not open generate.sh, $!";

print GENERATE "\#/bin/sh\n";
print GENERATE "sox /home/pilot/weather_station/media/WeatherStation_intro.wav ";


$linecounter = 0;

while($line = <WEATHER>)
{

    chop($line);

    # default arraycount can be overriden
    $arraycount = length($line);
#    print "MAIN: $linecounter $line\n";
    
    # ZULU TIME first line time  
    if($linecounter == 0)
    {
	generate_from_array($line);
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_zulu.wav ";	
    }
    # Wind Direction
    elsif($linecounter == 1)
    {
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_wind.wav ";
	if($arraycount == 1)
	{
    	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_0.wav ";
    	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_0.wav ";
	}
	elsif($arraycount == 2)
	{
    	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_0.wav ";
	}
	generate_from_array($line);
    }
    # Wind Speed
    elsif($linecounter == 2)
    {
	# doing wind
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_at.wav ";

	$ceil = ceil($line);

	$arraycount = length($ceil);
	generate_from_array($ceil);

	print GENERATE "/home/pilot/weather_station/media/WeatherStation_knot.wav ";

	
	
    }
    elsif($linecounter == 5)
    {
	# doing dewpoint
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_dewpoint.wav ";

	$arraycount = 2;
	generate_from_array($line);

	
    }
    # Altimeter
    elsif($linecounter == 3)
    {
	# doing altimeter
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_altimeter.wav ";

	if(length($line) > 5)
	{
	    $short = substr( $line, 0, 5 );
	    $line = $short;
	}
	$arraycount = 5;
	generate_from_array($line);

    }
    # TEMP
    elsif($linecounter == 4)
    {
	print GENERATE "/home/pilot/weather_station/media/WeatherStation_temp.wav ";

	$arraycount = 2;
	generate_from_array($line);
    }
    else
    {
	break;
    }

   $linecounter++;
	    

# round temp down
# round dewpoint down
# round altimter down
# round wind up
# replace wind direction digit with 0

}

# okay - now generate the script file to generate the wav file

print GENERATE "/home/pilot/weather_station/media/WeatherStation_0.wav /home/pilot/weather_station/ramdisk/weather.wav silence 1 0.25 0.1% -1 0.25 0.1%\n";
close(WEATHER);
close(GENERATE);


sub generate_from_array
{
    # get argument
    $info = $_[0];

    @carray = split(//,$info);


#    print "sub: $info @carry $arraycount\n";

    for($i=0;$i<$arraycount;$i++)
    {
#	print "$carray[$i]\n";
	if($carray[$i] == '0')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_0.wav ";
	}
	elsif($carray[$i] == '1')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_1.wav ";
	}
	elsif($carray[$i] == '2')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_2.wav ";
	}
	elsif($carray[$i] == '3')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_3.wav ";
	}
	elsif($carray[$i] == '4')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_4.wav ";
	}
	elsif($carray[$i] == '5')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_5.wav ";
	}
	elsif($carray[$i] == '6')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_6.wav ";
	}
	elsif($carray[$i] == '7')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_7.wav ";
	}
	elsif($carray[$i] == '8')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_8.wav ";
	}
	elsif($carray[$i] == '9')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_9.wav ";
	}
	elsif($carray[$i] == '.')
	{
	    print GENERATE "/home/pilot/weather_station/media/WeatherStation_point.wav ";
	}
	else
	{
	    print "Error: convert_weather_txt_to_wav.pl I am ran into $carray[$i]\n";
	}

    }
}
