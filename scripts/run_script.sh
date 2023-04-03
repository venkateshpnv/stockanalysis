#!/bin/bash

echo "Arguments: ${@}"
if [ $# -eq 0 ]; then
	echo "Invalid arguments"
	echo "$ ${0} run_file"
	echo "Example1: $ ${0} US_Update_Technicals"
	echo "Example2: $ ${0} Update_Price_Change \"US\" "
	exit
fi

export PYTHONWARNINGS="ignore"
HOME_DIR=/home/vpetla/work/stockanalysis
FILE=$1
SCRIPT="${FILE}.py"
log_file="${FILE}.txt"
yesterday_log_file="${HOME_DIR}/logs/${FILE}_yesterday.txt"
log_file="${HOME_DIR}/logs/${log_file}"
val=`ps ax | grep "python3 -u $HOME_DIR/$SCRIPT" | grep -v grep | wc -l`
if [ $val -ne 0 ]; then
    echo "Killing stale processes of $SCRIPT"
    pkill -9 -f "python3 -u $HOME_DIR/$SCRIPT"
fi
echo "Starting $SCRIPT"
/usr/bin/cp $log_file $yesterday_log_file
# Skip first argument of $@
shift
echo "cd $HOME_DIR && python3 -u $HOME_DIR/$SCRIPT $@ 2>&1  | tee $log_file"
echo "Starting Time `/usr/bin/date`" 2>&1 | tee $log_file
cd $HOME_DIR && /usr/bin/python3 -u $HOME_DIR/$SCRIPT $@ 2>&1  | tee -a $log_file
echo "Ending Time `/usr/bin/date`" 2>&1 | tee -a $log_file
