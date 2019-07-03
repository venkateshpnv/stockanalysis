#!/bin/sh

HOME_DIR=/home/vpetla/work/stockanalysis
SCRIPT=earnings_estimates.py

#export HOME=/root
#XAUTHORITY=/run/user/0/gdm/Xauthority

xhost +localhost
export DISPLAY=:0.0

me=`basename "$0"`
#echo $me
#crontab -u root -l | grep $me
#if [ $? -ne 0 ]; then
#		echo "Scheduling a crontab for $me"
#		(crontab -u root -l ; echo "@reboot /bin/sh $HOME/scripts/$me") | crontab -u root -
#fi

cd $HOME_DIR && python3 $SCRIPT >> $HOME_DIR/log_estimates 2>&1
if [ $? -e 0 ]; then
		echo "Completed fetching earnings estimates"
		#crontab -u root -l | grep -v 'build_earnings_estimates.sh'  | crontab -u root -
		#Delete cron job for earnings estimates
		crontab -u root -l | grep -v $me  | crontab -u root -
else
		echo "Taking DB Backup and rebooting"
		mongodump --db=Stocks --out=$HOME_DIR/db_backup
		cd $HOME_DIR && git add db_backup/*
		cd $HOME_DIR && git commit -m "Taking db backup with earnings_estimates"
		cd $HOME_DIR && git push origin master
		sleep 60
		reboot
fi
