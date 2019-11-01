#!/bin/bash

for i in {4..9}
do
	command_1="cat 100stas-wifi-sdn.txt | grep 'h1: \[  $i\]' > h1_sta$i.txt"
	echo $command_1
	eval $command_1
	command_2="cat 100stas-wifi-sdn.txt | grep 'h2: \[  $i\]' > h2_sta$i.txt"
	eval $command_2
done
for i in {10..53}
do
	command_1="cat 100stas-wifi-sdn.txt | grep 'h1: \[ $i\]' > h1_sta$i.txt"
	eval $command_1
	command_2="cat 100stas-wifi-sdn.txt | grep 'h2: \[ $i\]' > h2_sta$i.txt"
	eval $command_2
done
