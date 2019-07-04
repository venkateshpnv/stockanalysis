#!/bin/bash

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=earnings_estimates.py

export DISPLAY=:0.0
val=`ps ax | grep earnin | grep -v grep | wc -l`
if [ $val -eq 0 ]; then
	python3 $HOME_DIR/$SCRIPT
fi
