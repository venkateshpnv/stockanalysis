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

max_size = 50*1024*1024 # 50MB

def split(db_file, max_size, split_path):
    if not os.path.exists(split_path):
        os.mkdir(split_path)
    f = open(db_file,"rb")
    size = os.path.getsize(db_file)
    print(size)
    splits = math.ceil(size/max_size)
    print(splits)

    for i in range(splits):
        filex = split_path + "/US_Stocks.bson%r" %(i)
        print(filex)
        f.seek(i*max_size)
        buf = f.read(max_size)
        fx = open(filex, "wb")
        fx.write(buf)
        fx.close()

def combine(split_path, combine_name):
    #db_file = split_path+combine_name
    db_file = "/tmp/US_Stocks.bson"
    cmd = "rm -rf %s" %(db_file)
    os.system(cmd)
    #cmd = "touch %s" %(db_file)
    #os.system(cmd)
    f = open(db_file, "ab")
    print(f.tell())
    for (root,dirs,files) in os.walk(split_path, topdown=True):
        files.sort(key=natural_keys)
    for fx in files:
        fx = split_path+'/'+fx
        print(fx)
        #fxb = open(fx, "r")
        with open(fx, 'rb') as fxb:
            f.write(fxb.read())
    f.close()
        

dir_path = os.path.dirname(os.path.realpath(__file__))
split_path=dir_path+'/db_backup/Stocks/US_Stocks'
db_file = dir_path+'/db_backup/Stocks/US_Stocks.bson'
split(db_file, max_size,split_path)
#combine("/home/vpetla/work/stockanalysis/db_backup/Stocks/US_Stocks", "US_Stocks.bson")
