#!/bin/bash
sudo ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock \
                     --private-key=db:Open_vSwitch,SSL,private_key \
                      --certificate=db:Open_vSwitch,SSL,certificate \
                      --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
                      --pidfile --detach
