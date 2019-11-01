#!/bin/bash
awk '{t=substr($1,0,9);n=substr($9,0,length($9));if(t!=pt){print t,sum*8/1000000 > "h1_lte.txt";sum=0;}else{sum+=n;}pt=t;}' /tmp/h1_lte.out
awk '{t=substr($1,0,9);n=substr($9,0,length($9));if(t!=pt){print t,sum*8/1000000 > "h2_lte.txt";sum=0;}else{sum+=n;}pt=t;}' /tmp/h2_lte.out