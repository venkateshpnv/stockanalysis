from inspect import currentframe
import os
import sys
import pprint
import shutil
import subprocess
import time
import types

# Date
from datetime import datetime as dt, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date
import re
import pandas as pd
import numpy as np
import requests
from math import nan, isnan
from sklearn.preprocessing import MinMaxScaler, MaxAbsScaler
from scipy import stats
from kneed import KneeLocator
import copy
from os import path

import psutil

from itertools import cycle
import secrets
import multiprocessing

import internet
import DB

import datastructures

MAX_FAIL_COUNT=10
YEAR=1
QUARTER=2
MONTH=4
WEEK=8
DAY=16
ALL=0x1F

sender_email_id="petlafin@gmail.com"
receiver_email_id="petlafin@gmail.com"
sender_passwd="Tasche3#Gm"
proxy_list = None

def get_free_core(timeout=10000):
    cpus = psutil.cpu_percent(interval=0.1, percpu=True)
    count = 0
    while True or count == timeout/2:
        for i in range(cpus):
            if cpus[i] < 95:
                return i
        time.sleep(2)
        count = count + 1
    print("Couldn't find a free core even after 1000 seconds")
    return -1

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

def is_none_r_nan(a):
    if a is None:
        return True
    NumberTypes = (int, float)
    if isinstance(a, NumberTypes) and isnan(a):
        return True
    return False

def is_val(a):
    if a is not None:
        if isinstance(a, str) and len(a) > 0:
            return True
    return False

def is_number(a, check_non_zero=False):
    if isinstance(a, (int, float, complex)) and not isinstance(a, bool) is True and not isnan(a):
        if check_non_zero:
            return (a != 0)
        return True
    return False

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

def safe_substract(value1, value2):
    if value1 is None and value2 is None:
        return None
    if value1 is None:
        return -value2
    if value2 is None:
        return value1
    return (value1-value2)

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

def get_current_quarter():
    month = dt.now().date().month - 1
    quarter = (month // 3) + 1
    return quarter

# Lock without blocking
# Return False if lock is not available
# Acquire lock and return True if the lock is available.
# https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Lock.acquire
def unblocked_lock(lock):
    return lock.acquire(block=False)

def exception_info(E):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print("Exception: %s, filename: %r, line no: %d" %(exc_type, fname, exc_tb.tb_lineno))

def get_holiday_list(start=None, end=None, datetime_format=True):
    mysql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Data')
    query = 'select Date from {} where Date between \'{}\' and \'{}\''.format('US_Holiday_List', str(start), str(end))
    df = pd.read_sql_query(query, mysql_engine)
    DB.close_sql_connection(mysql_engine)

    if datetime_format:
        return [dt.strptime(x, "%Y-%m-%d").date() for x in list(df['Date'])]
    return list(df['Date'])

def get_duration_human(start, end):
    delta = relativedelta.relativedelta(end, start)
    dur = ""
    if delta.years > 0:
        dur = dur + str(delta.years) + " years"
    if delta.months > 0:
        dur = dur + str(delta.months) + " months"
    if delta.days > 0:
        dur = dur + str(delta.days) + " days"

    return dur

# Returns number of days between two days excluding weekends
# and holidays(if provided)
# start and end should be of type datetime.date()
# holidays should be a list of datetime.date objects
def date_difference(start, end, holidays=None):
    return np.busday_count(start, end, holidays=holidays)

# Compare two dataframes and return the difference rows (df1-df2)
# Return entries present in df1 but not in df2
def df_difference(df1,df2):
    #df = pd.concat([df1,df2])
    #df = df.reset_index(drop=True)
    #df_gpby = df.groupby(list(df.columns))
    #idx = [x[0]  for x in  df_gpby.groups.values() if len(x) == 1]
    #return df.reindex(idx)
    ## This should work too. Concat both. Drop duplicates. Rest is the difference.
    ##return pd.concat([df1,df2]).drop_duplicates(keep=False)
    return df1[~df1.apply(tuple,1).isin(df2.apply(tuple,1))]

# list difference (l1-l2)
# Return entries present in l1 but not in l2.
def list_difference(l1, l2):
    s = set(l2)
    diff = [x for x in l1 if x not in s]
    return diff
#Waste. Use the top one.
def list_difference2(li1, li2):
    return (list(list(set(li1)-set(li2)) + list(set(li2)-set(li1))))

proxy_lock = multiprocessing.Lock()

def delete_proxy_server(proxy_server):
    global proxy_list
    #proxy_server = bytes(proxy_server, 'utf-8')
    proxy_lock.acquire()
    if proxy_server in proxy_list:
        proxy_list.remove(proxy_server)
    proxy_lock.release()

def pull_proxies():
    global proxy_list
    now = dt.now()

    # If proxy list is
    # 1. empty or
    # 2. not yet fetched or
    # 3. fetched 30 min back
    # pull the proxies again
    proxy_lock.acquire()
    if proxy_list is None or \
            pull_proxies.then is None or \
            now-pull_proxies.then >= timedelta(minutes=30):
        #ret=requests.get("http://list.didsoft.com/get?email=petlanvenkatesh@gmail.com&pass=didsoftpnv&pid=http1000&showcountry=no")
        ret=requests.get("http://proxyfuel.com/gate2_list.txt")
        proxy_list = ret.content.splitlines()
        proxy_list = [m.decode("utf=8") for m in proxy_list]

        pull_proxies.then = now

        # Create a circular list of proxies
        #proxy_list = cycle(proxy_list)
    proxy_lock.release()

pull_proxies.then=None

def pull_proxies2():
    global proxy_list
    now = dt.now()
    url='https://www.proxy-list.download/HTTPS'
    proxy_lock.acquire()
    if proxy_list is None or \
            pull_proxies.then is None or \
            now-pull_proxies.then >= timedelta(minutes=30):
        page = internet.get_webpage(url)
        df = pd.read_html(page)
        if len(df)>= 1:
            df = df[0]
            df['IP_Port'] = df['IP'].astype(str)+':'+df['Port'].astype(str)
            proxy_list = df['IP_Port'].to_list()
    proxy_lock.release()

def pull_proxies3():
    global proxy_list
    now = dt.now()
    url='https://list.proxylistplus.com/SSL-List-1'
    proxy_lock.acquire()
    if proxy_list is None or \
            pull_proxies.then is None or \
            now-pull_proxies.then >= timedelta(minutes=30):
        page = internet.get_webpage(url)
        df = pd.read_html(page)
        if len(df)>= 1:
            df = df[2]
            df['IP_Port'] = df['IP address.1'].astype(str)+':'+df['Port'].astype(str)
            proxy_list = df['IP_Port'].to_list()
    proxy_lock.release()

def get_proxy():
    pull_proxies()
    #pull_proxies2()
    #return "http://petlanvenkatesh.gmail.com:proxy3pnv@gate2.proxyfuel.com:2000"
    #pull_proxies3()
    if proxy_list is None:
        return None
    #return next(proxy_list)
    # Randomly select a proxy
    #return secrets.choice(proxy_list).decode("utf-8")
    return secrets.choice(proxy_list)
    #return '110.39.0.30:8080'

def get_eod_token_id():
    with open(datastructures.eod_token_file, 'r') as f:
        data = f.read()
    return data.strip()

def get_telegram_token_id(token='stock_notify'):
    if token not in datastructures.telegram_tokens.keys() or \
            'token' not in datastructures.telegram_tokens[token].keys() or \
            not path.isfile(datastructures.telegram_tokens[token]['token']):
        return ""

    token_file = datastructures.telegram_tokens[token]['token']
    with open(token_file, 'r') as f:
        data = f.read()
        return data.strip()
    return ""

def get_telegram_chat_id(token='stock_notify'):
    if token not in datastructures.telegram_tokens.keys() or \
            'chat_id' not in datastructures.telegram_tokens[token].keys() or \
            not path.isfile(datastructures.telegram_tokens[token]['chat_id']):
        return ""

    token_file = datastructures.telegram_tokens[token]['chat_id']
    with open(token_file, 'r') as f:
        data = f.read()
        return data.strip()
    return ""

def disconnect_vpn():
    return
    subprocess.check_output('hotspotshield disconnect', shell=True)

def change_vpn():
    return
    cmd = 'hotspotshield status'
    s   = subprocess.check_output(cmd, shell=True)
    ss  = str(s)
    loc = ss.find('Session uptime')
    if loc > 0:
        uptime = ss[loc:].split('\\')[0].split(" ")[-1].split(':')
        # If less than an hour
        if len(uptime) < 3:
            uptime = int(uptime[0])
            if uptime < 30:
               return

    retries = 0
    done=False
    while not done:
        try:
            while not done:
                cmd="hotspotshield locations | cut -f 1 -d ' ' | shuf -n 1"
                s=subprocess.check_output(cmd, shell=True)
                loc = str(s)[2:].split("\\")[0]
                if loc.find('-') != -1:
                    break

                print("%s: Changing to location %s" %(dt.today(), loc))
                ret = subprocess.check_output('hotspotshield disconnect', shell=True)
                time.sleep(2)
                cmd = 'hotspotshield connect %s' %(loc)
                ret = subprocess.check_output(cmd, shell=True)
                time.sleep(5)
                status_retries=0
                while True:
                    cmd = 'hotspotshield status'
                    ret = subprocess.check_output(cmd, shell=True)
                    if ret.decode("utf-8").find('disconnected') > 0:
                        print("VPN is disconnected, retrying...")
                        if status_retries > 5:
                            retries = retries + 1
                            time.sleep(5)
                            break
                        status_retries = status_retries + 1
                        time.sleep(5)
                        continue
                    elif ret.decode("utf-8").find('connected') > 0:
                        done = True
                        break
                    else:
                        if status_retries > 5:
                            break
                        status_retries = status_retries + 1
                        time.sleep(5)
                        continue
                ##ret=b''
                #if ret.decode("utf-8") != '':
                if retries > 5:
                    print('Failed changing vpn... retrying')
                    break
                #retries = retries + 1
                time.sleep(5)
                continue
 
            #ret=b''
            #time.sleep(1)
        except subprocess.CalledProcessError:
            if retries > 5:
                break
            retries = retries + 1
            time.sleep(15)
            continue
        #time.sleep(5)
        if retries > 5:
            break
        #break

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
    shutil.rmtree(path)
    #filelist = [f for f in os.listdir(path)]
    #for f in filelist:
    #    file_path = "%s/%s" %(path, f)
    #    os.remove(file_path)
    #os.rmdir(path)

def create_dir(path):
    os.mkdir(path)

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

def CAGR(start, end, years):
    try:
        if start is None or end is None or years <= 0 or end == 0:
            return np.nan
        cagr = ((end/start)**(1/years))-1
        return cagr
    except Exception as E:
        print("start: %r, end: %r, years: %r" %(start,end,years))
        return np.nan

#def percent_change(st_price, en_price):
#    if st_price == 0:
#        return 0
#    if st_price < 0:
#        st_price = abs(st_price)
#        en_price = en_price + st_price
#
#    return float(en_price/st_price - 1)
def percent_change(st_price, en_price):
    flag = -1
    percentChange = 0.0

    try:
        if st_price is None or en_price is None:
            percentChange = np.nan
            return
        if st_price == 0:
            percentChange = en_price
        
        if st_price > 0 and en_price > 0:
            # st_price:7 en_price:10    
            if en_price >= st_price:
                percentChange = float(abs(en_price - st_price)/st_price)
            # st_price : 10 en_price: 7
            #elif en_price < st_price:
            else:
                percentChange = float((abs(en_price - st_price)/st_price)*flag)
        elif st_price < 0 and en_price < 0:
            # st_price: -7 en_price: -3
            if en_price >= st_price:
                percentChange = float(abs(en_price - st_price)/abs(st_price))
            # st_price: -3 en_price: -7
            #elif en_price < st_price:
            else:
                percentChange = float(abs(en_price - st_price)/abs(st_price)*flag)
         # st_price: 7 en_price: -3
        elif st_price > 0 and en_price < 0:
            percentChange = float(abs(en_price - st_price)/st_price*flag)
            # st_price: -3 en_price: 7
        elif st_price < 0 and en_price > 0:
                percentChange = float(abs(en_price - st_price)/abs(st_price))
    finally:
        return percentChange

def get_latest_figure(stk, statement_type, figure):
    if 'fig' in stk.keys():
        if 'financial-statements' in stk['fig'].keys():
            if statement_type in stk['fig']['financial-statements'].keys():
                years = list(stk['fig']['financial-statements'][statement_type].keys())
                dates = []
                for d in years:
                    if d != 'date':
                        dates.append(dt.strptime(d, "%m-%Y").date())
                dates = sorted(dates,reverse=True)
                if len(dates) > 0:
                    latest_date = dates[0].strftime('%m-%Y')
                    if latest_date in stk['fig']['financial-statements'][statement_type].keys():
                        if figure in stk['fig']['financial-statements'][statement_type][latest_date].keys():

                            return stk['fig']['financial-statements']['income-statement'][latest_date][figure]/1000

    return None

def df_format(x, thousands=False):
    if thousands:
        return "${:,.0f}K".format(x/1000)
    return "${:,.0f}".format(x)

def calculate_slope(df, scaler=True, transform=True, ordinal=True):
    slope = np.nan
    nrmse = np.nan
    try:
        if not isinstance(df,pd.DataFrame):
            print("Error: common.py: calculate_slope(): Not an instance of dataframe")
            return
 
        if df.empty:
            print("Error: common.py: calculate_slope(): Empty dataframe")
            return

        if len(df) <= 1:
            return

        # Normalize data.
        # You can also use scikitlearn's scaling function

        # This is a simple way to substract the mean and divide by std devivation.
        if scaler:
            if transform:
                #scaler = MinMaxScaler()
                scaler = MaxAbsScaler()
                df_transform = scaler.fit_transform(df)
                df_transform = pd.DataFrame(columns=list(df.columns), data=df_transform, index=df.index)

            else:
                # You don't need to transform the slopes
                # Set this to False if you are calculating a slope for a set of slopes
                df_transform = copy.deepcopy(df)
        else:
            df_transform = (df - df.mean())/df.std()
            #df_transform = (df - df.min())/(df.max() - df.min())

        if ordinal:
            df['Date'] = df.index
            df['Date_ordinal'] = pd.to_datetime(df['Date']).map(dt.toordinal)
            x_coordinates = df['Date_ordinal'].values
        else:
            x_coordinates = np.arange(len(df_transform))

        coefficients, residuals, _, _, _ = np.polyfit(x_coordinates, df_transform, 1, full=True)
        #coefficients, residuals, _, _, _ = np.polyfit(np.arange(len(df_transform)), df_transform, 1, full=True)
        slope = coefficients[0][0]
        # Mean Square Error
        if len(residuals) > 0:
            mse = residuals[0]/(len(df.index))
            # Normalised Root Mean Square Error
            nrmse = np.sqrt(mse)/(df_transform.max() - df_transform.min())
    except Exception as E:
            print("Error: common.py: calculate_slope(): %s" %(str(E)))
    finally:
        return slope, nrmse

def knee_locator_df(df, column, S, curve, direction, online=True):
    x=np.array(range(len(df)))
    y=list(df[column])
    return knee_locator(x, y, S, curve, direction, online)

# curve
# - concave[)(] for knee
# - convex[()] for elbow
# direction 
# - increasing for positive slope 
# - decreasing for negative slope
# online: 
# - False: (Knee/elbow as first element detected)
# - True: (correcting “old” knee/elbow values if necessary if points are received)
# S: Sensitivity for knee/elbow detection (S=0 or bigger); Satopää et alia [2] state that 
#    “kneedle” has perfect information in offline setting when sensitivity is 0 whereas in 
#    online settings, overall a sensitivity of 1 shows the best overall performance, 
#    but it can vary from the data points received.
def knee_locator(x, y, S, curve, direction, online=True):
    kneedle = KneeLocator(x, y, S=S, curve=curve, direction=direction, online=online)
    knee = kneedle.knee
    elbow = kneedle.elbow
    return knee,elbow

def set_cpu_affinity():
    while True:
        cpus  = psutil.cpu_percent(percpu=True)

        core_usage_percent = min(cpus)
        core = cpus.index(min(cpus))

        if core_usage_percent <= 70:
            # Set CPU affinity to that core if the usage percent is less than
            # 70 percent

            if core == 0:
                aff = 0
            else:
                aff = 0 | 1 << (core - 1)
            os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))
            return aff
        # Else, wait for a second and try again.
        time.sleep(1)

