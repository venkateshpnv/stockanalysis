#!/bin/sh

HOME_DIR=/home/vpetla/work/stockanalysis

echo "Automatic DB Backup"
mongodump --db=Stocks --out=$HOME_DIR/db_backup
python3 $HOME_DIR/file_split.py
cd $HOME_DIR && git pull origin master
cd $HOME_DIR && git add db_backup/*
cd $HOME_DIR && git rm db_backup/Stocks/US_Stocks.bson
cd $HOME_DIR && git commit -m "Automatic DB Backup"

cd $HOME_DIR && git push origin master
