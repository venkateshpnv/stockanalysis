from inspect import currentframe
import os
import pprint

# Date
import datetime
from datetime import datetime as dt, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date


YEAR=1
QUARTER=2
MONTH=4
WEEK=8
DAY=16
ALL=0x1F

sender_email_id="petlafin@gmail.com"
receiver_email_id="petlafin@gmail.com"
sender_passwd="Tasche3#Gm"

#Supportive calls
def PRINT_ERR(x):
    f = open("error_log.txt", "a")
    f.write(x)
    f.close()
    print("ERR: %s" %(x))
    
def PRINT_DBG(x):
    None
    #print(x)
def PRINT(x):
    None
    #print(x)

def pretty_print(entry):
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(entry)

def goto(linenum):
    global line
    line=linenum

def p2f(x):
    try:
        val = float(x.strip('%'))
    except ValueError:
        return 0
    return val

def str_to_int(x):
    try:
        val = int(x)
    except ValueError:
        return 0
    return val

def str_to_float(x):
    try:
        #val = float(x)
        val = float(x.lstrip().rstrip().replace("$","").replace(",","").replace("%",""))
    except ValueError:
        return float('NaN')
    except TypeError:
        return float('NaN')
    return val

def to_float(x):
    try:
        val = float(x)
    except Exception as e:
        print(x, val, str(e))
        return float('NaN')
    return val

def to_int(x):
    try:
        val = int(x)
    except Exception as e:
        print(x, val, str(e))
        return float('NaN')
    return val

def str_to_float_valid(x):
    try:
        val = float(x)
        return True
    except ValueError:
        return False

def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno

def write_to_file(html, html_file):
    f = open(html_file, "w")
    f.write(html)
    f.close()

def write_to_unparsed(stock):
    f = open("US_unparsed.txt", "a")
    f.write(stock)
    f.write("\n")
    f.close()
 
def lowest(a, b):
    if a < b:
        return a
    return b

def lowest_3(a, b, c):
    if a < b:
        low = a
    low = b
    if b < c:
        return b
    return c

import re

# Get last date of financial statements
def get_last_date(stk, dates, fmt):
    if 'date' in dates:
        i = dates.index('date')
        del dates[i]

    dt_dates=[]
    for d in dates:
        d = dt.strptime(d, fmt).date()
        dt_dates.append(d)
    dt_dates = sorted(dt_dates)
    if len(dt_dates) > 0:
        return dt_dates[-1]
    return dt.strptime("01-1950", "%m-%Y").date()

def years_to_days(y):
    today=dt.now().date()
    past=today-relativedelta(years=y)
    return (today-past).days

def p_atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ p_atoi(c) for c in re.split(r'(\d+)', text) ]

#Print Stock Info
def print_stock_info(stk):
    PRINT("Name: %r" %(stk['bscs']['name']))
    PRINT("Symbol: %r" %(stk['bscs']['symbol']))
    PRINT("Price: %r" %(stk['bscs']['price']))
    PRINT("Face Value: %r" %(stk['bscs']['face_value']))
    PRINT("Promoter Stake: %r" %(stk['bscs']['promoter_stake']))
    PRINT("Corporate Stake: %r" %(stk['bscs']['corp_stake']))
    PRINT("Public Stake: %r" %(stk['bscs']['pub_stake']))
    PRINT("FII Stake: %r" % (stk['bscs']['fii_stake']))
    PRINT("DII Stake: %r" % (stk['bscs']['dii_stake']))
    PRINT("Others Stake: %r" % (stk['bscs']['others_stake']))

def remove_dir(path):
    filelist = [f for f in os.listdir(path)]
    for f in filelist:
        file_path = "%s/%s" %(path, f)
        os.remove(file_path)
    os.rmdir(path)

def write_stock_to_file(val, filename, mode):
    filename = "/home/vpetla/work/stockanalysis/%s" %(filename)
    f = open(filename, mode)
    val=val+"\n"
    f.write(val)
    f.close()

def read_from_file(filename):
    filename = "/home/vpetla/work/stockanalysis/%s" %(filename)
    f = open(filename, "r")
    val=f.read()
    f.close()
    return val



