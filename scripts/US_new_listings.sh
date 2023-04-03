#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=US_new_listings.py

#while true
#do
#export DISPLAY=:0.0
val=`ps ax | grep "python3 -u $HOME_DIR/$SCRIPT" | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	echo "Starting $SCRIPT"
   	#python3 -u $HOME_DIR/$SCRIPT 2>&1 > /dev/null
   	python3 -u $HOME_DIR/$SCRIPT 2>&1 | tee $HOME_DIR/logs/US_newlistings.txt
	#unset DISPLAY
fi
#sleep 10
#done
