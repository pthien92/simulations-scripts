#!/bin/sh


# example how to remove interfaces and bridge
sudo ifconfig mybridge promisc down
sudo ifconfig thetap promisc down
sudo ifconfig thetap2 down
sudo ifconfig pgwtap down
sudo ifconfig pgwtap2 down
sudo ovs-vsctl del-port mybridge pgwtap
sudo ovs-vsctl del-port mybridge thetap
#sudo tunctl -d pgwtap
#sudo tunctl -d thetap
#sudo tunctl -d thetap2
sudo ip link delete pgwtap
sudo ip link delete pgwtap2
sudo ip link delete thetap
sudo ip link delete thetap2
sudo ovs-vsctl del-br mybridge


# for linux bridge

sudo ifconfig mybridge down
sudo ifconfig thetap down
sudo ifconfig pgwtap down
sudo brctl delif mybridge thetap
sudo brctl delif mybridge pgwtap
sudo brctl delbr mybridge