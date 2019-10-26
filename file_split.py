import os
import math

import re

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

db_file="/home/vpetla/work/stockanalysis/db_backup/Stocks/US_Stocks.bson"
max_size = 50*1024*1024 # 50MB

def split(db_file, max_size, store_path):
    if not os.path.exists(store_path):
        os.mkdir(store_path)
    f = open(db_file,"rb")
    size = os.path.getsize(db_file)
    print(size)
    splits = math.ceil(size/max_size)
    print(splits)

    for i in range(splits):
        filex = store_path + "/US_Stocks.bson%r" %(i)
        print(filex)
        f.seek(i*max_size)
        buf = f.read(max_size)
        fx = open(filex, "wb")
        fx.write(buf)
        fx.close()

def combine(store_path, combine_name):
    #db_file = store_path+combine_name
    db_file = "/tmp/US_Stocks.bson"
    cmd = "rm -rf %s" %(db_file)
    os.system(cmd)
    #cmd = "touch %s" %(db_file)
    #os.system(cmd)
    f = open(db_file, "ab")
    print(f.tell())
    for (root,dirs,files) in os.walk(store_path, topdown=True):
        files.sort(key=natural_keys)
    for fx in files:
        fx = store_path+'/'+fx
        print(fx)
        #fxb = open(fx, "r")
        with open(fx, 'rb') as fxb:
            f.write(fxb.read())
    f.close()
        

split(db_file, max_size,"/home/vpetla/work/stockanalysis/db_backup/Stocks/US_Stocks")
#combine("/home/vpetla/work/stockanalysis/db_backup/Stocks/US_Stocks", "US_Stocks.bson")
