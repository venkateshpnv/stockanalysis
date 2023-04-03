#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT='US_Update_Dividends.py'

val=`ps ax | grep "python3 -u $HOME_DIR/$SCRIPT" | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	echo "Starting $SCRIPT"
   	cd $HOME_DIR && python3 -u $HOME_DIR/$SCRIPT 2>&1  | tee $HOME_DIR/logs/US_Dividends.txt
fi
