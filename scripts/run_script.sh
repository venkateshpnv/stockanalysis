#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=US_EPS.py

#exec >> $HOME_DIR/EPS_History_log.txt 2>&1 
export DISPLAY=:0.0
val=`ps ax | grep $SCRIPT | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	killall firefox
	sleep 3
   	#script -a $HOME_DIR/EPS_History_log.txt && python3 $HOME_DIR/$SCRIPT
   	python3 -u $HOME_DIR/$SCRIPT 2>&1 | tee -a $HOME_DIR/EPS_History_log.txt
   	#python3 $HOME_DIR/$SCRIPT
fi
