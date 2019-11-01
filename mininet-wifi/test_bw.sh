#!/bin/bash
tcpdump -l -e -n port $2 -i $1 | awk '{t=substr($1,0,9);n=substr($9,0,length($9));if(t!=pt){print t,sum*8/1000000;sum=0;}else{sum+=n;}pt=t;}'
