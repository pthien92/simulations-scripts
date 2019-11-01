#!/bin/bash

# Omnet++ runs in command line mode, not using GUI
# Copy lteScenario to omnet/samples folder
omnet_dir="/path/to/omnetpp-5.0/"
cd $omnet_dir
./setenv
omnet_working_dir="$omnet_dir/samples/lteScenario/"
ns3_working_dir="path/to/ns-3.29/"


for simTime in {1..100}
do
	cd $omnet_working_dir
	opp_run -u Cmdenv lteCoreExampleOriginal.ini -l ../inet/src/INET -l ../lte/src/lte -c LTE-SDN 2>&1 > /dev/null &
	pid=$!
	cd $ns3_working_dir
	echo "Simulation time = $simTime"
	command="sudo ./waf --run 'lte-sdn --simTime=$simTime' >> omnet-ns3-8ues-new.txt"
	eval $command
	kill $pid
done

