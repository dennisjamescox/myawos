#!/usr/bin/perl
use strict;
use warnings;
use autodie;

my $BASE      = "/home/user/weather_station";
my $WEATHER_TXT = "$BASE/weather.txt";
my $GEN_SH    = "$BASE/generate.sh";
my $MEDIA     = "$BASE/media";
my $OUT_WAV   = "$BASE/current.wav";

# Audio output params
my $SOX_BITS   = 8;
my $SOX_CHANS  = 1;
my $SOX_RATE   = 8000;

# Map characters to audio files
my %CHAR_TO_WAV = (
  '0' => "$MEDIA/WeatherStation_0.wav",
  '1' => "$MEDIA/WeatherStation_1.wav",
  '2' => "$MEDIA/WeatherStation_2.wav",
  '3' => "$MEDIA/WeatherStation_3.wav",
  '4' => "$MEDIA/WeatherStation_4.wav",
  '5' => "$MEDIA/WeatherStation_5.wav",
  '6' => "$MEDIA/WeatherStation_6.wav",
  '7' => "$MEDIA/WeatherStation_7.wav",
  '8' => "$MEDIA/WeatherStation_8.wav",
  '9' => "$MEDIA/WeatherStation_9.wav",
  '.' => "$MEDIA/WeatherStation_point.wav",
  'Z' => "$MEDIA/WeatherStation_point.wav", # keep your original meaning
);

# Convenience for constant clips
my %CLIP = (
  intro     => "$MEDIA/WeatherStation_intro.wav",
  zulu      => "$MEDIA/WeatherStation_zulu.wav",
  wind      => "$MEDIA/WeatherStation_wind.wav",
  at        => "$MEDIA/WeatherStation_at.wav",
  knot      => "$MEDIA/WeatherStation_knot.wav",
  gusts     => "$MEDIA/WeatherStation_gusts.wav",
  altimeter => "$MEDIA/WeatherStation_altimeter.wav",
  temp      => "$MEDIA/WeatherStation_temp.wav",
  dewpoint  => "$MEDIA/WeatherStation_dewpoint.wav",
  point     => "$MEDIA/WeatherStation_point.wav",

  caution  => "$MEDIA/WeatherStation_caution.wav",
  weather_information_is => "$MEDIA/WeatherStation_weather_information_is.wav",
  hour     => "$MEDIA/WeatherStation_hour.wav",
  hours    => "$MEDIA/WeatherStation_hours.wav",
  old      => "$MEDIA/WeatherStation_old.wav",

    
    );


for my $clip (values %CLIP) {
  require_clip($clip);
}


open my $weather_fh, "<", $WEATHER_TXT;
open my $gen_fh,     ">", $GEN_SH;

print {$gen_fh} "#!/bin/sh\n";
print {$gen_fh} "sox $CLIP{intro} ";

my $weather_age_hours = weather_file_age_hours($WEATHER_TXT);

if ($weather_age_hours > 0) {
  print {$gen_fh} "$CLIP{caution} ";
  print {$gen_fh} "$CLIP{weather_information_is} ";

  emit_from_string($gen_fh, "$weather_age_hours");

  if ($weather_age_hours == 1) {
    print {$gen_fh} "$CLIP{hour} ";
  } else {
    print {$gen_fh} "$CLIP{hours} ";
  }

  print {$gen_fh} "$CLIP{old} ";
}

my $linecounter = 0;

while (my $line = <$weather_fh>) {
  chomp $line;

  if ($linecounter == 0) {
    # Zulu time string -> digits
      emit_from_string($gen_fh, $line);
    print {$gen_fh} "$CLIP{zulu} ";
  }
  elsif ($linecounter == 1) {
    # Wind direction
    print {$gen_fh} "$CLIP{wind} ";

    my $len = length($line);
    # pad to 3 digits with leading zeros (your original logic)
    if    ($len == 1) { print {$gen_fh} "$CHAR_TO_WAV{0} $CHAR_TO_WAV{0} "; }
    elsif ($len == 2) { print {$gen_fh} "$CHAR_TO_WAV{0} "; }

    emit_from_string($gen_fh, $line);
  }
  elsif ($linecounter == 2) {
    # Wind speed
    print {$gen_fh} "$CLIP{at} ";
    emit_from_string($gen_fh, $line, 0);
    print {$gen_fh} "$CLIP{knot} ";
  }
  elsif ($linecounter == 3) {
    # Max wind speed (gusts)
    print {$gen_fh} "$CLIP{gusts} ";
    emit_from_string($gen_fh, $line, 0);
    print {$gen_fh} "$CLIP{knot} ";
  }
  elsif ($linecounter == 4) {
    # Altimeter
    print {$gen_fh} "$CLIP{altimeter} ";
    emit_from_string($gen_fh, $line, 1); # altimeter mode
  }
  elsif ($linecounter == 5) {
    # Temp
    print {$gen_fh} "$CLIP{temp} ";
    emit_from_string($gen_fh, $line, 0);
  }
  elsif ($linecounter == 6) {
    # Dewpoint
    print {$gen_fh} "$CLIP{dewpoint} ";
    emit_from_string($gen_fh, $line, 0);
  }
  else {
    last;
  }

  $linecounter++;
}

# Finish sox command
print {$gen_fh} "-b $SOX_BITS -c $SOX_CHANS -r $SOX_RATE $OUT_WAV ";
print {$gen_fh} "silence 1 0.17 0.1% -1 0.17 0.1%\n";

close $weather_fh;
close $gen_fh;

# Make script executable (optional but handy)
chmod 0755, $GEN_SH;

exit 0;

sub emit_from_string {
  my ($fh, $info) = @_;

  my @chars = split //, $info;

  for (my $i = 0; $i < @chars; $i++) {
    my $ch = $chars[$i];

    if (exists $CHAR_TO_WAV{$ch}) {
      print {$fh} "$CHAR_TO_WAV{$ch} ";
    } else {
      warn "Unknown character '$ch' in input '$info' (index $i)\n";
    }
  }
}

sub require_clip {
  my ($path) = @_;
  die "Missing audio clip: $path\n" unless -f $path;
}

sub weather_file_age_hours {
  my ($path) = @_;

  my @stat = stat($path);
  return 0 unless @stat;

  my $mtime = $stat[9];
  my $age_seconds = time() - $mtime;

  return 0 if $age_seconds <= 3600;

  my $hours = int($age_seconds / 3600);
  $hours = 1 if $hours < 1;

  return $hours;
}
