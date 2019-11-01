#!/bin/bash
ryu-manager qos_controller.py --ofp-tcp-listen-port 6633 2>&1 >> /tmp/qos_controller.log &
ryu-manager learning_controller_13.py --ofp-tcp-listen-port 6653 2>&1 >> /tmp/learning_controller.log &
ryu-manager lte_adapter_switch_13.py --ofp-tcp-listen-port 6663 2>&1 >> /tmp/lte_adapter_switch_13.log &
