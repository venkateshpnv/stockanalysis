#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=US_Price.py

#export DISPLAY=:0.0
val=`ps ax | grep $SCRIPT | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	echo "Starting $SCRIPT"
   	#python3 -u $HOME_DIR/$SCRIPT 2>&1 > /dev/null
   	#python3 -u $HOME_DIR/$SCRIPT 2>&1 | tee -a $HOME_DIR/EPS_History_log2.txt
   	python3 $HOME_DIR/$SCRIPT
	#unset DISPLAY
fi
