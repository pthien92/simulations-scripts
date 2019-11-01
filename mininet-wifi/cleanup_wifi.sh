#!/bin/bash

for i in {1..10}
do
   command_1="sudo ifconfig ap$i-wlan1 down"
   eval $command_1
   command_2="sudo ip link delete ap$i-wlan1"
   eval $command_2
done

for i in {1..10}
do
   command_1="sudo ifconfig ap$i-eth2 down"
   eval $command_1
   command_2="sudo ip link delete ap$i-eth2"
   eval $command_2
done

for i in {1..4}
do
   command_1="sudo ifconfig s1-eth$i down"
   eval $command_1
   command_2="sudo ip link delete s1-eth$i"
   eval $command_2
done

for i in {1..3}
do
   command_1="sudo ifconfig s2-eth$i down"
   eval $command_1
   command_2="sudo ip link delete s2-eth$i"
   eval $command_2
done

for i in {1..10}
do
   command_1="sudo ifconfig s3-eth$i down"
   eval $command_1
   command_2="sudo ip link delete s3-eth$i"
   eval $command_2
done

for i in {0..20}
do 
   command_1="sudo ifconfig wlan$i down"
   eval $command_1
   command_2="sudo ip link delete wlan$i"
   eval $command_2
done
