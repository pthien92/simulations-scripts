#!/bin/bash

numberOfEnb=2
numberOfUePerEnb=2
for simTime in {1..100}
do
	echo "Simulation time = $simTime"
	command="sudo ./waf --run 'lte-sdn --simTime=$simTime' >> output-lte-4nodes.txt"
	eval $command
done
