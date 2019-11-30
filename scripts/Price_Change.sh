#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=$HOME_DIR/Update_Price_Change.py

#export DISPLAY=:0.0
val=`ps ax | grep $SCRIPT | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	echo "Starting $SCRIPT"
	echo > ~/tmp/price_change.txt
   	#python3 -u $HOME_DIR/$SCRIPT 2>&1 > /dev/null
   	python3 -u $SCRIPT $1 2>&1 | tee -a ~/tmp/price_change.txt
   	#python3 $SCRIPT
	#unset DISPLAY
fi
