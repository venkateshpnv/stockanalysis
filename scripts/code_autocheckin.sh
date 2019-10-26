#!/bin/sh

HOME_DIR=/home/vpetla/work/stockanalysis

cd $HOME_DIR && git add *.py
cd $HOME_DIR && git add file.txt nins.txt run_script_log.txt
cd $HOME_DIR && git add pips*
cd $HOME_DIR && git add scripts/*
#cd $HOME_DIR && git add supporting_files/*
cd $HOME_DIR && git commit -m "Automatic Code Backup"

cd $HOME_DIR && git push origin master
