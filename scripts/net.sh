#!/bin/bash

while true
do
hostname -I | grep -q 192.168
if [ $? -eq 1 ]; then
	systemctl restart NetworkManager.service
	sleep 120
fi
sleep 10
done
