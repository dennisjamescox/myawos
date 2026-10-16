#!/usr/bin/perl
use strict;
use warnings;
use autodie;
use JSON::PP qw(decode_json);
use POSIX qw(strftime);
use File::Basename qw(dirname);
use File::Temp qw(tempfile);

my $BASE = $ENV{MYAWOS_BASE} // "/home/user/weather_station";
my $WEATHER_TXT = "$BASE/weather.txt";
my $CLOUDS_JSON = "$BASE/clouds.json";
my $OUT = "$BASE/current_sms.txt";
my $MAX_WEATHER_AGE_HOURS = $ENV{MYAWOS_WEATHER_MAX_AGE_HOURS} // 12;

if (!weather_is_fresh($WEATHER_TXT, $MAX_WEATHER_AGE_HOURS)) {
    my ($out, $temp_name) = tempfile(".current_sms.XXXXXX", DIR => dirname($OUT), UNLINK => 0);
    print {$out} "No weather available at this time\n";
    close $out;
    rename $temp_name, $OUT;
    exit 0;
}

open my $weather, "<", $WEATHER_TXT;
my @values = map { chomp; $_ } <$weather>;
close $weather;
die "Expected seven weather values in $WEATHER_TXT\n" unless @values >= 7;

my ($out, $temp_name) = tempfile(".current_sms.XXXXXX", DIR => dirname($OUT), UNLINK => 0);
print {$out} "RWJ Airpark (54T) Advisory Weather\n";
print {$out} "$values[0] Zulu time\n";
my $observation_timestamp = (stat($WEATHER_TXT))[9];
print {$out} strftime("%H:%M:%S %Y-%m-%d", localtime($observation_timestamp)), " Local time\n";
print {$out} "Wind $values[1] at $values[2] knots Gusts $values[3] knots\n";
print {$out} "Altimeter $values[4]\n";
print {$out} "Temperature $values[5] Dewpoint $values[6]\n";

my $cloud_text = read_cloud_text($CLOUDS_JSON);
print {$out} "$cloud_text\n" if $cloud_text ne "";
close $out;
rename $temp_name, $OUT;

sub read_cloud_text {
    my ($path) = @_;
    return "" unless -f $path;
    open my $fh, "<", $path;
    local $/;
    my $raw = <$fh>;
    close $fh;
    my $data = eval { decode_json($raw) };
    return "" unless ref($data) eq "HASH";
    return "" if ($data->{cache_status} // "") eq "unavailable";
    return $data->{text} // "";
}

sub weather_is_fresh {
    my ($path, $max_age_hours) = @_;
    my @stat = stat($path);
    return 0 unless @stat;
    return (time() - $stat[9]) < ($max_age_hours * 3600);
}
