#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=Update_Price_Change.py

#export DISPLAY=:0.0
val=`ps ax | grep 'python3 $SCRIPT' | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
   	echo > /tmp/India_pricechange.txt
	echo "Starting $SCRIPT"
   	#python3 -u $HOME_DIR/$SCRIPT 2>&1 > /dev/null
   	python3 -u $HOME_DIR/$SCRIPT 'India' 2>&1 | tee -a /tmp/India_pricechange.txt
	#unset DISPLAY
fi
