#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT='python3 US_analysis.py'

val=`ps ax | grep $SCRIPT | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	echo "Starting $SCRIPT"
   	cd $HOME_DIR && python3 -u $HOME_DIR/$SCRIPT 2>&1  | tee $HOME_DIR/logs/US_Stocks.txt
fi
