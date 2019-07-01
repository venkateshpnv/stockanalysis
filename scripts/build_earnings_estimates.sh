#!/bin/sh

HOME_DIR=/home/vpetla/work/stockanalysis
cd $HOME_DIR && python3 earnings_estimates.py >> $HOME_DIR/log_estimates 2>&1
if [ $? -ne 0 ]; then
		echo "Taking DB Backup and rebooting"
		mongodump --db=Stocks --out=$HOME_DIR/db_backup
		cd $HOME_DIR && git add db_backup/*
		cd $HOME_DIR && git commit -m "Taking db backup with earnings_estimates"
		cd $HOME_DIR && git push origin master
		#reboot
fi
