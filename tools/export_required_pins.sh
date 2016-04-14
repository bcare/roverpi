#!/bin/bash


## read the configuration file to detect the pins that must be exported :
configfile=$1

grep 'pin_pwm.*= *[0-9]\+;*' $configfile > powerpins.txt
grep 'pin_direction.*= *[0-9]\+;*' $configfile  > directionpins.txt
grep 'pin_monitor.*= *[0-9]\+;*' $configfile  > monitorpins.txt
grep 'pin_headlights.*= *[0-9]\+;*' $configfile > extrapins.txt


sed 's/.*=[ ]*\([0-9]\+\)[ ]*;.*$/\1/g' powerpins.txt > outputpins.txt
sed 's/.*=[ ]*\([0-9]\+\)[ ]*;.*$/\1/g' directionpins.txt >> outputpins.txt
sed 's/.*=[ ]*\([0-9]\+\)[ ]*;.*$/\1/g' monitorpins.txt > inputpins.txt
sed 's/.*=[ ]*\([0-9]\+\)[ ]*;.*$/\1/g' extrapins.txt >> outputpins.txt

for pin in `cat outputpins.txt  | sort | uniq`;
do
	echo "exporting pin $pin mode output"
	gpio export $pin out
done

for pin in `cat inputpins.txt | sort | uniq`;
do
	echo "exporting pin $pin mode input"
	gpio export $pin in
done


rm powerpins.txt
rm directionpins.txt
rm monitorpins.txt
rm outputpins.txt
rm inputpins.txt

		  
