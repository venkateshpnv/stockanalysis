#!/bin/sh

HOME_DIR=/home/vpetla/work/stockanalysis

echo "Automatic DB Backup"
mongodump --db=Stocks --out=$HOME_DIR/db_backup
cd $HOME_DIR && git add db_backup/*
cd $HOME_DIR && git commit -m "Automatic DB Backup"

cd $HOME_DIR && git add *.py
cd $HOME_DIR && git add pips
cd $HOME_DIR && git add scripts/*
cd $HOME_DIR && git add supporting_files/*
cd $HOME_DIR && git commit -m "Automatic Code Backup"

cd $HOME_DIR && git push origin master
