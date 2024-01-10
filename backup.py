#!/usr/bin/python3

# Backup all mysql and mongodb databases and store on the pendrive.

import sys
import os
from os import path
from datetime import datetime as dt
import multiprocessing
import time

pendrive_path='/mnt/pendrive_backup/'
mysql_host = '10.89.45.241'
mongodb_host='10.89.45.49'
mysql_username='vpetla'
mysql_passwd='petla123'
remove_list = ['Database', 'information_schema', 'mysql', 'performance_schema', 'sys', '']

#db_size = { 'US_Stocks' : 4403933006,
#            'US_Stocks_Beta     
#US_Stocks_Changes        
#US_Stocks_Data           
#US_Stocks_Fin            
#US_Stocks_Fin_Change     
#US_Stocks_Options        
#US_Stocks_Short_Interests
#US_Stocks_Technicals 

def mongodb_backup(location_dir, mongodb_host, db=None):
    #Take the mongodb backup
    if not path.exists(location_dir + '/mongodb_backup'):
        cmd = 'mkdir -p ' + location_dir + '/mongodb_backup'
        ret = os.system(cmd)
        if ret != 0:
            print("Failed to create the directory %r/mongodb_backup" %(location_dir))
            return False
    
    #mongodump --forceTableScan --host 10.89.45.49 --db=Stocks --out=/mnt/pendrive_backup/18-07-2021/mongodb_backup
    cmd = 'mongodump --forceTableScan --host ' + \
            mongodb_host + \
            ' --db=Stocks ' + \
            ' --out=' + location_dir + '/mongodb_backup'
    ret = os.system(cmd)
    if ret != 0:
        print("Failed to take mongodb stocks backup")
    cmd = 'mongodump --forceTableScan --host ' + \
            mongodb_host + \
            ' --db=Cryptos ' + \
            ' --out=' + location_dir + '/mongodb_backup'
    ret = os.system(cmd)
    if ret != 0:
        print("Failed to take mongodb cryptos backup")
        return False
 
    print('MongoDB backup completed')
    return True

def runcmd(cmd):
    ret = os.system(cmd)
    if ret != 0:
        print("Failed to run cmd: %r" %(cmd))
        return False
    return True

def mysql_backup(location_dir, mysql_host, username, passwd):

    #mysql -h 10.89.45.241 -u vpetla --password=petla123 -e "show databases;"
    if not path.exists(location_dir):
        os.mkdir(location_dir)
    
    cmd='mysql -h ' + mysql_host + ' -u ' + username + ' --password=' + passwd + ' -e "show databases;"'
    stream=os.popen(cmd)
    output=stream.read()
    if len(output) > 0:
        dbs = output.split('\n')
        if len(dbs) > 0:
            try:
                i = 0
                for r in remove_list:
                    dbs.remove(r)
                    i = i + 1
            except Exeception as E:
                print(str(E))
    
            if i != len(remove_list):
                print("Unknown dbs list")
                return False

    processes = [None]*len(dbs)
    try:
        for i, db in enumerate(dbs):
            db_file = location_dir + '/' + db + '.sql'
            if path.exists(db_file):
                cmd = 'rm -rf ' + db_file
                print("Deleting %s" %(db_file))
                ret = os.system(cmd)
                if ret != 0:
                    print('Failed to delete existing database backup file %r' %(db_file))
                    continue
                #cmd = 'mysqldump -h 10.89.45.241 -p US_Stocks_Fin -u vpetla --password=petla123 > /mnt/pendrive_backup/31-07-2021/US_Stocks_Fin.sql'
            cmd = 'mysqldump -h ' + mysql_host + \
                    ' -p ' + db + \
                    ' -u ' + username + \
                    ' --password=' + passwd + \
                    ' > ' + location_dir + '/' + \
                    db + '.sql'
            #processes[i] = multiprocessing.Process(target=runcmd, args=(cmd,db))
            #processes[i].start()
            print("Taking backup for %s" %(db))
            if runcmd(cmd) == False:
                return False
            print("%s backup completed" %(db))
    finally:
        for i in range(len(dbs)):
            if processes[i] is not None:
                processes[i].join()

    print('Mysql db backup completed')
    return True

if __name__ == "__main__":

    today = str(dt.now().date())
    location_dir = pendrive_path + today
    if path.exists(location_dir):
        print("Backup taken on %s. No need again" %(today))
        sys.exit(0)

    print("location: %s" %(location_dir))
    if mongodb_backup(location_dir, mongodb_host) == False:
        cmd = 'rm -rf ' + location_dir
        runcmd(cmd)
        sys.exit(1)
    if mysql_backup(location_dir, mysql_host, mysql_username, mysql_passwd) == False:
        cmd = 'rm -rf ' + location_dir
        runcmd(cmd)
        sys.exit(1)
