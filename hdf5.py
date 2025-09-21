import pandas as pd
import pandas_datareader as pdr
import h5py
from datetime import date, timedelta, datetime as dt
import time
from dateutil.relativedelta import relativedelta
from pandas.tseries.holiday import get_calendar
import sqlalchemy
import os
#from arctic import Arctic
import threading
from math import nan, isnan
import numpy as np
import copy
from io import StringIO
import time


import internet
from common import *
from datastructures import *
import DB

#hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/US_price_data.hd5'
hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/test.h5'
US_hdf_store_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/hdf_store2.h5'
India_hdf_store_path='/home/vpetla/work/stockanalysis/India_Stocks/DCF_Calc/hdf_store2.h5'

lock = threading.Lock()
fail_lock = threading.Lock()
vpn_lock = threading.Lock()
US_Cal = get_calendar('USFederalHolidayCalendar')

vpn_change_time = dt.now()

def construct_price_data_url(symbol, start, end, index=False):
    url = 'https://eodhd.com/api/eod/'+symbol
    if index:
        url = url + '.INDX?'
    else:
        url = url + '.US?'
    url = url + 'from='+str(start)\
                +'&to='+str(end)\
                +'&api_token='+get_eod_token_id()\
                +'&period=d'
    return url
 
def get_stock_data(country, stk, start, end, vpn_event=None, tick=None, proxy=False, eod_token=False):
    global vpn_change_time
    global vpn_lock
    pdrDatareader = False

    retries = 1
    conn_retries = 0
    df = pd.DataFrame()
    symbol = stk['bscs']['symbol'].replace('.','-')
    while True:
        try:
            if vpn_event and vpn_event.is_set() is False:
                print("**** %s: DF: Waiting..  for VPN change" %(symbol))
                vpn_event.wait()
                print("**** %s: DF: Waking up" %(symbol))

            if country == 'India' and symbol not in India_indices.keys():
                symbol = symbol + '.BO'

            if eod_token:
                if 'quoteType' in stk['bscs'].keys() and stk['bscs']['quoteType'] == 'Index':
                    url = construct_price_data_url(symbol, start, end, index=True)
                else:
                    url = construct_price_data_url(symbol, start, end, index=False)
                try:
                    ret = requests.get(url)
                    if ret.status_code == 402 or int(ret.headers['X-RateLimit-Remaining']) < 1 :
                        remaining_time = int(ret.headers['X-RateLimit-Remaining']) + 1
                        print("%s: Ratelimit: waiting for remaining time %d secs " %(stk['bscs']['symbol'], remaining_time))
                        if vpn_event:
                            vpn_event.clear()
                            time.sleep(remaining_time)
                            vpn_event.set()
                        else:
                            time.sleep(10)
                        continue
                    elif ret.status_code == 404:
                        print("Failed to get price data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                        update = True
                        return df
                    elif ret.status_code != 200:
                        print("Failed to get price data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                        return df
                except Exception as E:
                    print("get_stock_data(): Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
                    if isinstance(E, x-ratelimit-remaining):
                        remaining_time = int(ret.headers['X-RateLimit-Remaining']) + 1
                        print("%s: ratelimit exception. sleep remaining time %d and retry." %(stk['bscs']['symbol'], remaining_time))
                        if vpn_event:
                            vpn_event.clear()
                            time.sleep(remaining_time)
                            vpn_event.set()
                        else:
                            time.sleep(10)
                        continue
                    return

                #print("%s: Ratelimit: %r" %(stk['bscs']['symbol'], int(ret.headers['X-RateLimit-Remaining'])))
                df  = pd.read_csv(StringIO(ret.text), skipfooter=0, parse_dates=[0], index_col=0, engine='python')
                df.rename(columns={'Adjusted_close':'Adj Close'}, inplace=True)

            elif not pdrDatareader:
                if proxy:
                    proxy_server = get_proxy()
                    print("df: hdf5.py: proxy_server: %s" %(proxy_server))
                    df = tick.history(proxy=proxy_server, start=start, end=end)
                else:
                    df = tick.history(start=start, end=end)
                if 'Dividends' in list(df.columns):
                    del df['Dividends']
                if 'Stock Splits' in list(df.columns):
                    del df['Stock Splits']
                df['Adj Close'] = df['Close']
            else:
                if proxy:
                    proxies = {'http': get_proxy(),
                               'https': get_proxy()
                            }
                    headers = {     "Accept":"application/json",
                                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                                    "Accept-Encoding":"none",
                                    "Accept-Language":"en-US,en;q = 0.8",
                                    "Connection":"keep-alive",
                                    "Referer":"https://cssspritegenerator.com",
                                    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, \
                                     like Gecko) Chrome/23.0.1271.64 Safari/537.11"
                                }

                    with requests.Session() as s:
                        #s.headers = headers
                        s.proxies.update(proxies)
                        df = pdr.DataReader(symbol,'yahoo',start, end, retry_count=3, session=s)
                else:
                    df = pdr.DataReader(symbol,'yahoo',start, end, retry_count=3)
            df = df.astype('float64')
        except requests.exceptions.ProxyError as E:
            PRINT_ERR("hdf5.py: %s: %s:  Proxy Error, retrying" %(symbol, proxy_server))
            delete_proxy_server(proxy_server)
            continue

        except (KeyError, pdr._utils.RemoteDataError, IndexError) as E:
            if vpn_event:
                if retries  > 1:
                    PRINT_ERR("Unable to get DF for %s"%(symbol))
                    DB.update_price_failcount(stk, country, df=True)
                    break
                if vpn_event.is_set() is False:
                    print("**** Exception : %s: DF: Waiting..  for VPN change" %(symbol))
                    vpn_event.wait()
                    print("**** Exception : %s: DF: Waking up" %(symbol))
                    continue
                else:
                    time.sleep(2)
                    vpn_lock.acquire()
                    #print("**** %s: Got VPN lock" %(symbol))
                    now  = dt.now()
                    diff = now - vpn_change_time
                    # if vpn has not changed atleast a minutue ago, change it. else no use of changing it again.
                    if diff.seconds > 300:
                        #print(now, vpn_change_time)
                        vpn_event.clear()
                        #print("**** %s: Changing VPN " %(symbol))
                        change_vpn()
                        vpn_change_time = dt.now()
                        vpn_event.set()
                        #print("**** %s: VPN Changed" %(symbol))
                    retries = retries + 1
                    vpn_lock.release()
                    #print("**** %s: Released VPN lock" %(symbol))
                    continue
            else:
                if retries  > 1:
                    PRINT_ERR("Unable to get DF for %s"%(symbol))
                    DB.update_price_failcount(stk, country, df=True)
                    fail_lock.acquire()
                    count=len(open("/home/vpetla/work/stockanalysis/get_price_fails.txt").readlines())+1
                    f = open("/home/vpetla/work/stockanalysis/get_price_fails.txt", "a")
                    f.write("%s: %s: %s\n"%(count, symbol, stk['bscs']['name']))
                    f.close()
                    fail_lock.release()
                    break
                retries = retries + 1
                time.sleep(2)
                print("**** %s: DF: Retrying to get stock data" %(symbol))
                continue
 
        #except (urllib3.exceptions.NewConnectionError, OpenSSL.SSL.SysCallError) as E:
        except Exception as E:
            if conn_retries > 1:
                PRINT_ERR("Unable to get DF for %s"%(symbol))
                fail_lock.acquire()
                count=len(open("/home/vpetla/work/stockanalysis/get_price_fails.txt").readlines())+1
                f = open("/home/vpetla/work/stockanalysis/get_price_fails.txt", "a")
                f.write("%s: %s: %s\n"%(count, symbol, stk['bscs']['name']))
                f.close()
                fail_lock.release()
 
                break
            PRINT_ERR("%s: hdf5.py : Connection Error, retrying" %(symbol))
            time.sleep(1)
            conn_retries = conn_retries + 1
            continue
        break
    return df

def get_hdf_store_path(country):
    if country == 'US':
        return US_hdf_store_path
    else:
        return India_hdf_store_path
 
def hdf_replace_dataset(hdf_path, symbol, rdf):
    try:
        #lock.acquire()
        with h5py.File(hdf_path,mode='w') as f1:
            entry = symbol+'/table'
            del f1[entry]
            f1.create_dataset(entry, data=rdf)
        with h5py.File(hdf_path,mode='r') as f1:
            df = f1[symbol]['table']
            print(df.tail(10))
    finally:
        #lock.release()
        True

def open_hdf_store(country):
    if country == 'US':
        return pd.HDFStore(US_hdf_store_path, mode='a', complevel=9, complib='bzip2')
    if country == 'India':
        return pd.HDFStore(India_hdf_store_path, mode='a', complevel=9, complib='bzip2')

def get_symbols_hdf_store(country):
    symbols = []
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            symbols = store.keys()
        #with h5py.File(path, 'r') as f:
        #    symbols=list(f.keys())
    finally:
        lock.release()
    return symbols

def write_to_hdf_store(country, df, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            store[symbol] = df
    finally:
        lock.release()

def read_from_hdf_store(country, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            df = store[symbol]
    except Exception as e:
        store.close()
        print("remove_from_hdf_store: %r" %(str(e)))
        return pd.DataFrame()
    finally:
        lock.release()

def read_from_hdf_store_nolock(country, symbol):
    path = get_hdf_store_path(country)
    with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
        df = store[symbol]
    return df

def remove_from_hdf_store(country, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            symbol = '/' + symbol
            if symbol in store.keys():
                store.remove(symbol)
            else:
                PRINT_ERR("Symbol: %r not found. Unable to delete the dataframe")
    except Exception as e:
        store.close()
    finally:
        lock.release()
    return df

def remove_all_df_duplicates(country):
    symbols = get_symbols_hdf_store('US')
    for symbol in symbols:
        print(symbol)
        df = read_from_hdf_store(country, symbol)
        if df is not None and not df.empty and df.index.has_duplicates:
            print("duplicates in %r" %(symbol))
            df=df[~df.index.duplicated(keep='last')]
            #df = df.drop_duplicates(keep='last')
            #write_to_hdf_store(country, df, symbol)

def remove_df_duplicates(df):
    if df is not None and not df.empty and df.index.has_duplicates:
        df = df.sort_index()
        #df = df.drop_duplicates()
        df = df[~df.index.duplicated(keep='last')]
        #df = df.drop_duplicates(keep='last')
    return df

def read_df_from_mongodb(symbol, col):
    df=pd.DataFrame(list(col.find({'symbol':symbol}))[0]['series'])
    return df

def insert_df_from_hdf_to_mongodb(symbol, df, col):
    stock={}
    stock['symbol'] = symbol
    df.index=df.index.strftime("%Y-%m-%d")
    stock['series'] = df.to_dict()
    col.insert(stock)

def insert_all_dfs_from_hdf_to_mongodb(country):
    symbols = get_symbols_from_hdf(country)
    c = DB.open_db_client()
    db = c['Stocks']
    if country == 'US':
        col = db.US_Stocks_Prices
    elif country == 'India':
        col = db.India_Stocks_Prices
    else:
        PRINT_ERR("insert_all_dfs_to_mongodb(): Unknown Country %r" %(country))
        DB.close_db_client(c)
        return

    i = 0
    for symbol in symbols:
        print("%r"%(symbol))
        df = read_from_hdf(country, symbol)
        insert_df_from_hdf_to_mongodb(symbol, df, col)
        i = i + 1
        if i > 100:
            break

    DB.close_db_client(c)

def insert_df_from_hdf_to_sql(country, symbol, engine, table):
    df = read_from_hdf(country, symbol)
    df['Symbol'] = symbol
    df['Date'] = df.index.strftime("%Y-%m-%d")
    df.index = df['Date'] #Is this required? Anyway index will be truncated by sql
    query = 'select * from '+ table + ' where symbol=%r' %(symbol)
    rdf = pd.read_sql_query(query, engine)
    if not rdf.empty:
        rdf.index = rdf['Date']
        df = df[~df.Date.isin(rdf.Date)]
    if not df.empty:
        df.to_sql(name=table,con=engine,index=False,if_exists='append')

def insert_all_dfs_from_hdf_to_sql(country):
    table = 'US_Stocks'
    symbols = get_symbols_from_hdf(country)
    engine=sqlalchemy.create_engine("mysql+pymysql://vpetla:petla123@localhost:3306/sample_db")

    i = 0
    for symbol in symbols:
        if i > 1783:
            print("%d: %r"%(i, symbol))
            insert_df_from_hdf_to_sql(country, symbol, engine, table)
        i = i + 1

#def write_to_hdf_store(country, df, symbol):
#    if country == 'India':
#        store = library = 'India_Stocks_Prices'
#    else:
#        store = library = 'US_Stocks_Prices'
#    try:
#        with Arctic('localhost') as st:
#           if library not in store.list_libraries:
#                st.initialize_library(library)
#            lib = st[library]
#            lib.write(symbol, df)
#    finally:
#        return

#def read_from_hdf_store(country, symbol):
#    df = pd.DataFrame()
#    if country == 'India':
#        store = library = 'India_Stocks_Prices'
#    else:
#        store = library = 'US_Stocks_Prices'
#    try:
#        with Arctic('localhost') as st:
#           if library not in store.list_libraries:
#                st.initialize_library(library)
#            lib = st[library]
#            if lib.has_symbol(symbol):
#                df  = lib.read(symbol).data
#    except Exception as e:
#        print(str(e))
#        return pd.DataFrame()
#    finally:
#        return df

def get_symbols_from_hdf(country):
    symbols = []
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
    except Exception as e:
        f.close()
    finally:
        lock.release()
    return symbols

def get_dataframe(country, sym, start=None, end=None):
    path = get_hdf_store_path(country)
    try:
        lock.acquire()
        df = pd.read_hdf(path, sym)
    except Exception as e:
        PRINT_ERR(str(e))
        lock.release()
        return pd.DataFrame()
    lock.release()
    if start == None:
        sindex = None
    else:
        sindex = get_nearest_index(df, start)
    if end == None:
        eindex = None
    else:
        eindex = get_nearest_index(df, end)+1
    return df[sindex:eindex]

def read_from_hdf(country, symbol, start=None, end=None):
    rdf=pd.DataFrame() 
    try:
        lock.acquire()
        path = get_hdf_store_path(country)
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
            if symbol not in symbols:
                raise Exception('Not found')
        rdf  = pd.read_hdf(path, symbol)
    except Exception as e:
        print("read_from_hdf(): symbol: %r, error: %r" %(symbol, str(e)))
    finally:
        lock.release()
    if start == None:
        sindex = None
    else:
        sindex = get_nearest_index(rdf, start)
    if end == None:
        eindex = None
    else:
        eindex = get_nearest_index(rdf, end)+1
    return rdf[sindex:eindex]

def delete_from_hdf(country, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
            if symbol in symbols:
                del f[symbol]
                time.sleep(1)
    except Exception as e:
        #f.close()
        pass
    finally:
        lock.release()

def write_to_hdf(country, df, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
            if symbol in symbols:
                del f[symbol]
                time.sleep(1)
        df.to_hdf(path, key=symbol, mode='a', format='table', append=True, complevel=9, complib='zlib')
    except Exception as e:
        #f.close()
        pass
    finally:
        lock.release()

def remove_from_hdf(country, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
            if symbol in symbols:
                del f[symbol]
    finally:
        lock.release()
    return symbols

# Exclude weekends and holidays. Return closest trading day
def get_valid_date(country, d):
    diff = d.weekday() - 4
    #If weekend take friday entry
    if diff > 0:
        d = d - timedelta(days=diff)
    # If it is holiday
    if country == 'US':
        while True:
            if d in US_Cal.holidays():
                d = d - timedelta(1)
            else:
                break
    return d

#Get price change with different inputs
# Price change in a 
# - days hdf_price(change('US', 'AAPL', df, 10) (or days=10)
# - months hdf_price_change('US', 'AAPL', df, months=6)
# - years hdf_price_change('US', 'AAPL', df, years=1)
# - range hdf_price_change('US', 'AAPL', df, start='2018-08-01', end='2019-06-12')
# - price change since start till date hdf_price_change('US', 'AAPL', df)
# - price change since a particular date till today hdf_price_change('US', 'AAPL', df, since='2017-08-12')
# - price change since start till a particular date hdf_price_change('US', 'AAPL', df, end='2014-02-11')
def hdf_price_change(country, sym=None, df=None, days=None, weeks=None, months=None, years=None, start=None, end=None, index=None):
#def hdf_price_change(country, sym, df, num_days):
    hour = 13
    if country is None:
        print("Please provide country")
        return None
    if country == 'India': # India
        hour=15
    if df is None:
        if not sym:
            print("No dataframe or symbol provided")
            return None
        #df = get_dataframe(country, sym)
        df = read_from_hdf(country, sym)
    if end:
        end = dt.strptime(end, '%Y-%m-%d')
    else:
        end = dt.now()
        if end.hour < hour:
            end = end - timedelta(1)
        end = get_valid_date(country, end.date())
    if years:
        start = end - relativedelta(years=years)
        start = get_valid_date(country, start)
    elif months:
        start = end - relativedelta(months=months)
        start = get_valid_date(country, start)
    elif weeks:
        start = end - relativedelta(weeks=weeks)
        start = get_valid_date(country, start)
    elif days:
        start = end - relativedelta(days=days)
        start = get_valid_date(country, start)
    elif start:
        start = dt.strptime(start, '%Y-%m-%d')
    else:
        #print("no args, take from start")
        #Price Change since beginning
        since = DB.get_since(country, sym)
        if since:
            start = dt.strptime(since, "%Y-%m-%d").date()
        else:
            start = df.index[0].date()
 
    en_price = hdf_get_price(sym, df, end)
    st_price = hdf_get_price(sym, df, start)
    if st_price == 0:
        return 0
    chg = (en_price/st_price - 1)
    if index:
        return chg, (en_price-st_price)
    return chg

# get the index of the nearest date entry for a particular dataframe.
# example if date is 27-oct-2019 sunday, the nearest date the stock
# has traded will be friday 25-oct-2019. If friday is a holiday,
# the nearest date will be 24-oct-2019.
# if the date is 24-oct-2019, its nearest will be the same date.
def get_nearest_index(df, req_date, tolerance=pd.Timedelta('2Y')):
    l = list(df.index)
    #l = df.index.to_list()
    try:
        # get the index of the entry
        i = l.index(pd.Timestamp(str(req_date)))
        #while True:
        #    x = df.index.get_loc(str(req_date), method='nearest', tolerance=tolerance)
        #    if x.size != 0:
        #        return int(x)
        #    req_date = req_date - relativedelta(months=3)
        index = i
    except Exception as e:
        # If entry does not exists, add the entry to the list,
        # sort the list and find the entry location.
        # return entry location - 1. if entry location is zero, return 1
        l.append(pd.Timestamp(str(req_date)))
        l.sort()
        #if pd.Timestamp(str(req_date)) > l[0]:
            #print("entry greater than first entry")
        i = l.index(pd.Timestamp(str(req_date)))
        if i != 0:
            cur = l[i]
            before = l[i - 1]
            if i < len(l)-1:
                after  = l[i + 1]
                if (cur - before) < (after - cur):
                    # Take previous entry
                    #index = df.index.to_list().index(before)
                    index = df.index.get_loc(before)
                else:
                    #index = df.index.to_list().index(after)
                    index = df.index.get_loc(after)
            else:
                #index = df.index.to_list().index(before) 
                index = df.index.get_loc(before)
        else:
            index = i
    return index
    #return df.index.get_loc(req_date, method='nearest', tolerance=30)

def hdf_get_price(sym, df, req_date):
    # Get nearest date entry not greater than 30 days
    # if the required date entry does not exist

    #if req_date is None, return first trading day price
    index = 0
    if req_date:
        try:
            index = get_nearest_index(df, req_date)
        except Exception as e:
            print("hdf_get_price: %r: sym: %r: %r" %(str(req_date), sym, str(e)))
            index=-1
    #print("index: %r" %(index))
    df = df.iloc[index]
    #print("df: %r" %(df))
    price = df['Adj Close']
    #print("price: %r" %(price))
    return price
    #return df.iloc[df.index.get_loc(date, method='nearest')]['Adj Close']
    #return df.loc[date]['Adj Close']

def get_latest_price(country, sym):
    df = read_from_hdf(country, sym)
    #df = get_dataframe(country, sym)
    if not df.empty:
        return df['Adj Close'][-1]
    return None

#Get lowest price between a particular date range
def hdf_get_low(df, start, end):
    rdf=df.loc[start:end]
    return rdf['Adj Close'].min()

#Get highest price between a particular date range
def hdf_get_high(df, start, end):
    rdf=df.loc[start:end]
    return rdf['Adj Close'].max()

# Get highest price in last num_days
def hdf_get_high_n_days(df, num_days):
    end = dt.now().date()
    start = end - relativedelta(days=num_days+1)
    return hdf_get_high(df, start, end)

# Get lowest price in last num_days
def hdf_get_low_n_days(df, num_days):
    end = dt.now().date()
    start = end - relativedelta(days=num_days+1)
    return hdf_get_low(df, start, end)


#def price_change_hdf(country, sym, name, num_days, data_type):
#    rdf=pd.read_hdf(hdf_path, sym)
#
#    end_date = list(rdf.index)[-1].date()
#    start_date = end_date - relativedelta(days=num_days)
#
#    #st_price = rdf.loc[start_date]['Adj Close']
#    en_price = rdf.iat[-1, rdf.columns.get_loc('Adj Close')]
#    st_price = read.iat[0, read.columns.get_loc('Adj Close')]
#    change = en_price/st_price - 1

def add_beta_columns(df, duration):
    key = '{}_beta'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_alpha'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_r_squared'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_alpha_pure'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_volatility'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_std'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_coef_var'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_qcd'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_bear_market'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_bull_market'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_index_cagr'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_index_percent_chg'.format(duration) #done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_cagr'.format(duration) # done
    if key not in list(df.keys()):
        df[key]=nan
    key = '{}_percent_chg'.format(duration) # done
    if key not in list(df.keys()):
        df[key]=nan
    return df

def get_df_for_duration(country, df, duration):
    #start, end = df.close[0], df.close[-1]
    #    return (end - start) / start
    end   = df.index[-1]
    start = end - duration
    start = get_valid_date(country, start)
    if start >= df.index[0]:
        return df[start:end]
    #rdf = df.last('6M') # last 6 months
    return pd.DataFrame() 

def hdf_calculate_betas(df, rdfb, rdf, index, duration):
    try:
        years = (rdf.index[-1]-rdf.index[0]).days/365.25
    except Exception:
        print("hdf_get_betas():",str(e))
        return df
    ## Take symbol's indexes as inputs
    ## For example, the recession happened in 2008.
    ## If the symbol started trading in 2011, the symbol's dataframe will not have
    ## info in 2008 but the S&P 500 does. The S&P 500 then takes the entries of 2008
    ## and uses it as the start where as the symbol started in 2011.
    ## To avoid this ambiquity, take symbol's timestamps as the indices for the S&P500
    ## (Pdb) df.index[0]
    ## Timestamp('2011-01-26 00:00:00')
    ## (Pdb) df.index[-1]
    ## Timestamp('2019-11-15 00:00:00')
    ## (Pdb)
    #rdfb = dfb[df.index[0]:df.index[-1]]
    
    # Calculate CAGR
    s_first = rdf[0]
    if isinstance(s_first, complex):
        print("first is complex number")
    s_last = rdf[-1]
    if isinstance(s_last, complex):
        print("last is complex number")
    
    growth_percent = s_last/s_first - 1
    key = '{}_percent_chg'.format(duration)
    df.loc[index][key] = growth_percent
    
    try:
        cagr = round((((s_last/s_first)**(1/years))-1), 4)
    except Exception as e:
        print(str(e))
        print("Failed to calculate CAGR for : %r" %(sym))
        print("First: %r, last: %r, years: %r" %(s_first, s_last, years))
        cagr = None
        #sys.exit()
    key = '{}_cagr'.format(duration)
    df.loc[index][key] = cagr
    
    first = rdfb[0]
    last  = rdfb[-1]
    
    key = '{}_index_percent_chg'.format(duration)
    df.loc[index][key] = last/first - 1
    
    key = '{}_index_cagr'.format(duration)
    b_cagr = df.loc[index][key] = round((((last/first)**(1/years))-1), 4)
    
    #print("Years: %r, first: %r, last: %r, cagr: %r, cagr_b: %r" %(round(years,2), first, last, round(cagr,4), round(b_cagr,4)))
    
    # from daily data points, create a time-series of monthly data points
    time_period=12. #months
    rts = rdf.resample('M').last()
    rbts = rdfb.resample('M').last()
    dfsm = pd.DataFrame({'s_adjclose' : rts,
                            'b_adjclose' : rbts},
                            index=rts.index)
    
    # compute returns
    dfsm[['s_returns','b_returns']] = dfsm[['s_adjclose','b_adjclose']]/\
        dfsm[['s_adjclose','b_adjclose']].shift(1) -1
    dfsm = dfsm.dropna()
    covmat = np.cov(dfsm["s_returns"],dfsm["b_returns"])
    
    # calculate measures now
    key = '{}_beta'.format(duration)
    beta = df.loc[index][key] = covmat[0,1]/covmat[1,1]
    
    alpha= np.mean(dfsm["s_returns"])-beta*np.mean(dfsm["b_returns"])
    df.loc[index]['{}_alpha_pure'.format(duration)] = np.mean(dfsm["s_returns"])-np.mean(dfsm["b_returns"])
    #print("alpha: %r" %(alpha))
    
    ypred = alpha + beta * dfsm["b_returns"]
    SS_res = np.sum(np.power(ypred-dfsm["s_returns"],2))
    SS_tot = covmat[0,0]*(len(dfsm)-1) # SS_tot is sample_variance*(n-1)
    
    key = '{}_r_squared'.format(duration)
    df.loc[index][key] = 1. - SS_res/SS_tot
    
    # 5- year volatiity and 1-year momentum
    volatility = np.sqrt(covmat[0,0])
    
    #momentum = np.prod(1+dfsm["s_returns"].tail(12).values) -1
    
    # annualize the numbers
    prd = 12. # used monthly returns; 12 periods to annualize
    #alpha = alpha*prd
    key = '{}_alpha'.format(duration)
    df.loc[index][key] = alpha*time_period
    
    #alpha_pure = alpha_pure*time_period
    #alpha pure
    key = '{}_alpha_pure '.format(duration)
    df.loc[index][key] = round(cagr - b_cagr, 4)
    
    #volatility
    key = '{}_volatility'.format(duration)
    df.loc[index][key] = volatility*np.sqrt(time_period)
    
    #Standard Deviation
    key = '{}_std'.format(duration)
    df.loc[index][key]= rdf.pct_change().std()
    
    #Coefficient of Variation
    key = '{}_coef_var'.format(duration)
    df.loc[index][key]= rdf.std() / rdf.mean()
    
    #QCD
    q1, q3 = rdf.quantile([0.25, 0.75])
    key = '{}_qcd'.format(duration)
    df.loc[index][key]= (q3 - q1) / (q3 + q1)
    
    #Is Bear Market? True/False
    #Is Bull Market? True/False
    start, end = rdf[0], rdf[-1]
    key = '{}_bear_market'.format(duration)
    if (((end - start) / start) <= -.2):
        df.loc[index][key] = 1 # True
        df.loc[index]['{}_bull_market'.format(duration)] = 0 #False
    else:
        df.loc[index][key] = 0 #False
        df.loc[index]['{}_bull_market'.format(duration)] = 1 # True

    return df

def hdf_get_beta(country, sym, df=None, dfb=None):
    betas = {}
    if df is None:
        try:
            #from pandas_datareader.quandl import QuandlReader
            #df = pdr.get_data_stooq(sym, retry_count=3)
            #print(df)
            #df = get_dataframe(country, sym)
            df = read_from_hdf(country, sym)
        except KeyError:
            print("Could not get data. Failed to calculate beta")
            return None

    if dfb is None:
        try:
            if country == 'US':
                bindex = "SP500"
            elif country == 'India':
                bindex = "BSE" 
            else:
                PRINT_ERROR("Unknown country. Unable to calculate beta for %s" %(sym))
                return betas
            #dfb = get_dataframe(country, bindex, df.index[0], df.index[-1])
            dfb = read_from_hdf(country, bindex, df.index[0], df.index[-1])
        except KeyError:
            print("Could not get data. Failed to calculate beta")
            return None

    df = add_beta_columns(df, 'six_months')
    df = add_beta_columns(df, 'one_year')
    df = add_beta_columns(df, 'five_years')
    df = add_beta_columns(df, 'whole')

    #rdf = df['Adj Close'].last('6M') # last 6 months
    for index,row in df[::-1].iterrows():
        print("symbol: %r, index: %r"%(sym, index))
        duration = 'six_months'
        if isnan(df.loc[index]['{}_beta'.format(duration)]):
            rdf = get_df_for_duration(country, df[:index]['Adj Close'], relativedelta(months=6))
            df = hdf_calculate_betas(df, dfb[:index]['Adj Close'], rdf, index, duration)

        duration = 'one_year'
        if isnan(df.loc[index]['{}_beta'.format(duration)]):
            rdf = get_df_for_duration(country, df[:index]['Adj Close'], relativedelta(years=1))
            df = hdf_calculate_betas(df, dfb[:index]['Adj Close'], rdf, index, duration)

        duration = 'five_years'
        if isnan(df.loc[index]['{}_beta'.format(duration)]):
            rdf = get_df_for_duration(country, df[:index]['Adj Close'], relativedelta(years=5))
            df = hdf_calculate_betas(df, dfb[:index]['Adj Close'], rdf, index, duration)

        duration = 'whole'
        if isnan(df.loc[index]['{}_beta'.format(duration)]):
            df = hdf_calculate_betas(df, dfb[:index]['Adj Close'], df['Adj Close'], index, duration)

    return df
 
#def hdf5_update_betas(symbol, df):
#    pass

def update_field_change(df, nans, field, duration, whole_change=False):
    for i in nans:
        loc = df.index.get_loc(i)
        if loc == 0:
            continue
        end = df.loc[i]
        if whole_change:
            start_loc = 0
        else:
            start_loc = get_nearest_index(df, i - duration)
        if start_loc == loc:
            start_loc = loc - 1

        st_price = df.iloc[start_loc]['Adj Close']
        en_price = df.loc[i]['Adj Close']
        if st_price == 0:
            change = 0
        else:
            change = en_price/st_price - 1

        df.loc[i, field] = float(change)
        #df.loc[i][field] = change
    return df

# Update df daily, weekly etc percent change
def update_percent_change(df, fields=price_change_fields.keys(), durations=price_change_fields.values()):
    write = False
    for f in fields:
        if f not in list(df.keys()):
            df[f] = nan

    for i in range(len(durations)):
        # Get all rows where the '%s Change' is empty
        #nans=df.index[isnan(df[fields[i]])]
        #nans = df[1:].index[df[fields[i]].isnull()]
        is_nan=df[fields[i]].isnull()
        # Is this required?
        #if df.index[1]-df.index[0] > timedelta(365):
        #    nans = (df[1:][fields[i]])[is_nan]
        #else:
        #    nans = df[fields[i]][is_nan]
        nans = df[fields[i]][is_nan]
        if not nans.empty and len(nans.index) > 1:
            df = update_field_change(df, nans.index, fields[i], durations[i])
            write = True

    # Same logic but for "Whole Change" field
    is_nan=df[fields[-1]].isnull()
    #if df.index[1]-df.index[0] > timedelta(365):
    #    nans = (df[1:][fields[-1]])[is_nan]
    #else:
    #    nans = df[fields[-1]][is_nan]
    nans = df[fields[-1]][is_nan]
    if not nans.empty:
        nans = nans[1:]
    if len(nans) > 0:
        df = update_field_change(df, nans.index, fields[-1], 0, whole_change=True)
        write = True

    return df, write

# Update day change, week change, month change etc till 10 year and whole percent change in the price of the stock for every day and update it in the df
def update_percent_change_all(country):
    fields = price_fields + [*price_change_fields]

    mysql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', 3036, 'US_Stocks')
    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection(country, db)
    stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
 
    try:
        i = 1
        for stk in stocks:
            if i < 0: #Skipped 574 STKCLF
                i = i + 1
                continue
            symbol = stk['bscs']['symbol']
            print("%d: %s: %s" %(i, symbol, stk['bscs']['name']))
            df = read_from_hdf(country, symbol)
            if df.empty:
                print(" %s Empty" %(symbol))
            else:
                df, status = update_percent_change(df)
                if status:
                    #write_to_hdf(country, copy.deepcopy(df), symbol)
                    DB.check_n_write_to_sql(mysql_engine, DB.get_symbol_table_name(symbol), copy.deepcopy(df), fields)
            i = i + 1
    finally:
        DB.close_db_client(c)
        DB.close_sql_connection(mysql_engine)

def update_bulk_price_data(stk, stk_df, collection=None, sql_engine=None, i=None, sem=None):
    if i is not None:
        aff = 0 | 1 << i%DB.num_cores
        os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    local_mdb = False
    local_sql = False
    if not collection:
        c = DB.open_db_client()
        db = c['Stocks']
        collection = db.US_Stocks
        local_mdb = True
    if not sql_engine:
        sql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')
        local_sql = True

    symbol = stk['bscs']['symbol']
    try:
        table = DB.get_symbol_table_name(symbol)
        query='select Date from ' + table + ' order by Date desc limit 1' 
        rdf = DB.read_from_sql(query, sql_engine)
        if len(rdf) != 1:
            printf("Table for symbol %s doesn't exist, skipping bulk update" %(symbol))
            return
        if rdf.iloc[-1]['Date'] != str(DB.get_previous_trading_day().date()):
            print("Symbol : %s price data was updated on %s date which is not the previous date. Skipping bulk update for this symbol" %(symbol, rdf.iloc[-1]['Date']))
            return
        if stk_df.iloc[0]['Date'] != str(DB.get_latest_trading_day().date()):
            print("Symbol : %s, stk date: %s, latest trading day: %s, latest price data is not same as latest trading day. Skipping bulk update for this symbol" %(symbol, stk_df.iloc[0]['Date'], str(DB.get_latest_trading_day())))
            return
        
        DB.mysql_update_table(sql_engine, DB.get_symbol_table_name(stk['bscs']['symbol']), stk_df, insert=True, check=True, date_column=False, format_columns=False)
        DB.update_field(collection, stk['bscs']['symbol'], "price_change.price", stk_df['Adj Close'][-1])
        DB.update_field(collection, stk['bscs']['symbol'], "price_change.volume", int(stk_df['Volume'][-1]))
        DB.update_field(collection, stk['bscs']['symbol'], "failcount.mysql_price_failcount", 0)
        DB.update_field(collection, stk['bscs']['symbol'], "dates.mysql_price_date", DB.get_latest_trading_day())
        DB.update_field(collection, stk['bscs']['symbol'], "dates.mysql_price_pull_date", dt.combine(dt.now(), dt.min.time()))
        DB.update_field(collection, stk['bscs']['symbol'], "dates.mysql_price_pull_success", True)
        #multiprocessing.Process(target=internet.update_price_change, args=('US', copy.deepcopy(stk), core, None, False)).start()
        print("%d: Symbol: %s, date: %s bulk eod price update completed" %(i, symbol, str(DB.get_latest_trading_day())))

    finally:
        if local_mdb:
            DB.close_db_client(c)
        if local_sql:
            DB.close_sql_connection(sql_engine)
        if sem:
            sem.release()

def add_new_symbol(d, db, sem=None):
    # vpeta: Update technicals to True, tracking=True, only_mongo=False after reenabling subscription
    DB.add_symbol_to_database(d, db, tracking=False, only_mongo=True, technicals=False)
    stks = db.US_Stocks.find({'bscs.symbol': d['Symbol']})
    stk = stks[0]
    if 'General' in stk.keys() and \
            isinstance(stk['General'], dict) and \
            stk['General']['Type'] == 'Common Stock':
        if 'tracking' in stk['bscs'].keys() or \
            stk['General']['Exchange'] in major_exchanges:
            DB.add_all_stock_data(stk)
    if sem:
        sem.release()
 
def bulk_update_price_volume(country, db=None, sql_engine=None):
    local_mdb = False
    local_sql = False
    if db is None:
        c = DB.open_db_client()
        db = c['Stocks']
        local_mdb = True
    if sql_engine is None:
        collection = DB.get_collection(country, db)
        sql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
        local_sql = True


    sort = [1, -1][dt.now().day % 2 == 0]
    num_processes = DB.num_cores * 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    i = 0
    j = 0

    # The data fetch from this bulk API will only contain today's price data.
    # Incase if the stock was not updated with the price information for sometime,
    # you might miss the old data if you only update today's data.
    # To overcome this issue, check if the stock has up-to-date price data till the 
    # last trading day and then add today's data. Else don't touch that stock.
    # They will be taken care in a different execution path.
    #stocks = db.US_Stocks.find({"$and" : [\
    #                                        {'General.Type':'Common Stock'},\
    #                                        #{'General.Exchange':{"$in":major_exchanges}},\
    #                                        {"$or": [\
    #                                                    {'General.Exchange':{"$in":major_exchanges}},\
    #                                                    {"$and": [ \
    #                                                                {'General.Exchange':{"$nin":major_exchanges}},\
    #                                                                {'bscs.tracking':{'$exists':True}}, \
    #                                                            ] \
    #                                                    },\
    #                                                ]\
    #                                        },\
    #                                        {'dates.technicals_pull_date': {'$gte':DB.get_latest_trading_day()}},\
    #                                        {'dates.mysql_price_date':{'$eq': DB.get_previous_trading_day()}},\
    #                                        {"$or": [\
    #                                                    {'failcount.mysql_price_failcount': {'$exists': False}},\
    #                                                    {"failcount.mysql_price_failcount":{"$lt": MAX_FAIL_COUNT}}\
    #                                                ]\
    #                                        },\
    #                                        #{"$or": [\
    #                                        #            {"bscs.lastSplitUpdateDate": {"$exists": False}},\
    #                                        #            {"bscs.lastSplitUpdateDate":{"$lte": dt.now()-timedelta(7)}}\
    #                                        #        ]\
    #                                        #},\
    #                                    ]\
    #                            }).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",sort]]).allow_disk_use(True)
    stocks = db.US_Stocks.find({"$and" : [ \
                                            {"dates.mysql_price_date": {"$eq": DB.get_previous_trading_day()}},\
                                            {"General.IsDelisted": False},\
                                            {'General.Type':'Common Stock'},\
                                            #{"$or": [\
                                            #            {'General.Exchange':{"$in":major_exchanges}},\
                                            #            {"$and": [ \
                                            #                        {'General.Exchange':{"$nin":major_exchanges}},\
                                            #                        {'bscs.tracking':{'$exists':True}}, \
                                            #                    ] \
                                            #            },\
                                            #        ]\
                                            #},\
                                            #{'dates.technicals_pull_date': {'$eq':DB.get_latest_trading_day()}},\
                                            #{"$or": [\
                                            #            {'failcount.mysql_price_failcount': {"$exists": False}},\
                                            #            {'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                                            #        ]\
                                            #}
                                        ]\
                                }\
                                ).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",sort]]).allow_disk_use(True)

    print("Total bulk stock candidates: %r" %(stocks.count()))

    df = pd.DataFrame()
    if stocks.count() > 0:
        url='https://eodhd.com/api/eod-bulk-last-day/US?api_token='+get_eod_token_id()+'&date='+str(DB.get_latest_trading_day().date())
        ret = requests.get(url)
        df  = pd.read_csv(StringIO(ret.text), skipfooter=0, parse_dates=[0], index_col=0, engine='python')
        df.rename(columns={'Adjusted_close':'Adj Close'}, inplace=True)
        df['Symbol'] = df.index
        if 'Ex' in df.columns:
            del df['Ex']

        i = 0
        t = None
        try:
            #for index, d in df.iterrows():
            for stk in stocks:
                stk_df = df[df['Symbol'] == stk['bscs']['symbol']]
                if not stk_df.empty:
                    try:
                        print("Bulk Update: %r: sno: %r: %r: %r" %(i, stk['sno'], stk['General']['Code'], stk['General']['Name']))
                    except Exception as E:
                        print("bulk_update: error: %s" %(str(E)))
                        print("Bulk Update: %r: sno: %r: %r" %(i, stk['sno'], stk['bscs']['symbol']))
                    stk_df.index = stk_df['Date']
                    del stk_df['Symbol']
 
                    sem.acquire()
                    #update_bulk_price_data(stk, stk_df, db.US_Stocks, sql_engine, i%DB.num_cores, sem)
                    processes[i%num_processes] = multiprocessing.Process(target=update_bulk_price_data, args=(copy.deepcopy(stk), stk_df, None, None, i, sem))
                    processes[i%num_processes].start()
                    i = i + 1
        finally:
            for j in range(len(processes)):
                if processes[j] is not None:
                    processes[j].join()

    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    i = 0
    print("Checking if any new symbols are added")
    try:
        syms = DB.get_symbols_from_mongo()
        #if len(df) > 0:
        #    for index, d in df.iterrows():
        #        #stks = db.US_Stocks.find({'bscs.symbol': d['Symbol']})
        #        #if stks.count() == 0:
        #        if not pd.isna(d['Symbol']) and d['Symbol'] not in syms:
        #            sem.acquire()
        #            add_new_symbol(d, db, sem)
        #            #processes[i%num_processes] = multiprocessing.Process(target=add_new_symbol, args=(d, db, sem))
        #            #processes[i%num_processes].start()
        #            i = i + 1
        api_token=get_eod_token_id()
        url = f'https://eodhd.com/api/exchange-symbol-list/US?api_token={api_token}&fmt=json'
        response = requests.get(url)
        if response.status_code == 200:
            tickers = response.json()
            df = pd.DataFrame(tickers)
            df.rename(columns={'Code': 'Symbol'}, inplace=True)
            df = df[df['Type']=='Common Stock']
            if len(df) > 0:
                for index, d in df.iterrows():
                    if not pd.isna(d['Symbol']) and d['Symbol'] not in syms:
                        sem.acquire()
                        try:
                            add_new_symbol(d, db, sem)
                            #processes[i%num_processes] = multiprocessing.Process(target=add_new_symbol, args=(d, db, sem))
                            #processes[i%num_processes].start()
                        except Exception as E:
                            print(f"Add symbol error: {str(E)}")
                            if sem:
                                sem.release()
                    else:
                        stocks = db.US_Stocks.find({"bscs.symbol":d['Symbol']})
                        if stocks.count() > 0:
                            s = stocks[0]
                            if 'General' not in s.keys():
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Code", d['Symbol'])
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.IsDelisted", False)
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Type", d['Type'])
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Exchange", d['Exchange'])
                            elif 'General' in s.keys() and 'IsDelisted' not in s['General'].keys():
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Code", d['Symbol'])
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.IsDelisted", False)
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Type", d['Type'])
                                DB.update_field(db.US_Stocks, d['Symbol'], "General.Exchange", d['Exchange'])


    finally:
            for j in range(len(processes)):
                if processes[j] is not None:
                    processes[j].join()
            if local_mdb:
                DB.close_db_client(c)
            if local_sql:
                DB.close_sql_connection(sql_engine)



def update_dataframe_price_volume(country, db, sql_engine, symbol, symbols, stk, core, sem, vpn_event=None, eod_token=True, percent_change=True, check_since_ipo_date=False):

    if core is not None:
        aff = 0 | 1 << core
        #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
        #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
        os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    data_update = False
    data_pull = False

    local_mdb = False
    local_sql = False
    if not db:
        c = DB.open_db_client()
        db = c['Stocks']
        local_mdb = True
    if not sql_engine:
        sql_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')
        local_sql = True

    if stk is None:
        print("hdf5: stk none, skipping %s: %s" %(stk['bscs']['symbol'], stk['bscs']['name']))
        DB.close_db_client(c)
        DB.close_sql_connection(sql_engine)
        if sem:
            sem.release()
        return

    if country == 'India':
        indices = India_indices
    else:
        indices = US_indices 

    df=pd.DataFrame() 
    collection = DB.get_collection(country, db)
    try:
        today=dt.now()
        #end=dt.now().date()# - timedelta(7)
        end = DB.get_latest_trading_day().date()
        #Updating the price and volume for the first time
        if stk['bscs']['symbol'] in indices.keys():
            index  = True
            symbol = indices[stk['bscs']['symbol']]
        else:
            index  = False
            symbol = stk['bscs']['symbol']
        #symbol = '/' + stk['bscs']['symbol']

        table = DB.get_symbol_table_name(symbol)

        #if not index and (len(symbols) == 0 or symbol not in symbols):
        if False:
            # Check if symbol is ending with +, =, -
            # Delete those junk symbols from mongodb
            if re.match(r'.*[\+|\=|\-]$', symbol):
                print("Deleting Junk Symbol: %r" %(symbol))
                db.US_Stocks.remove({"bscs.symbol" : symbol})
                db.US_Stocks_List.remove({"symbol" : symbol})
            else:
                start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
                print("New symbol: getting data for %r" %(stk['bscs']['symbol']))
                df = get_stock_data(country, stk, start, end, vpn_event, eod_token=eod_token)
                data_pull = True 
                # Sometimes yahoo gives wrong data. Wrong data will have volume as 0. Discard those rows
                if 'Volume' in df.columns:
                    df.drop(df[df['Volume']==0].index, inplace=True)
                #df = remove_df_duplicates(df)
                if not df.empty:
                    #df['Symbol'] = symbol
                    df['Date'] = df.index.strftime("%Y-%m-%d")
                    df.index = df['Date'] #Is it required?
                    #DB.write_to_sql(sql_engine, symbol, df)
                    print("mysql: %s: %s"%(symbol,stk['bscs']['name']))
                    #DB.check_n_write_to_sql(sql_engine, DB.get_symbol_table_name(symbol), copy.deepcopy(df), list(df.columns))
                    DB.mysql_update_table(sql_engine, DB.get_symbol_table_name(symbol), copy.deepcopy(df), insert=True, check=True, date_column=False, format_columns=False)
                    # Update the date on which the price is updated
                    #DB.update_field(collection, symbol, "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))
                    DB.update_field(collection, symbol, "price_change.price", df['Adj Close'][-1])
                    if not index:
                        # Reset mysql_price_failcount
                        DB.update_field(collection, symbol, "failcount.mysql_price_failcount", 0)
                        DB.update_field(collection, symbol, "price_change.volume", df['Volume'][-1])
                        data_update = True
                    if percent_change:
                        multiprocessing.Process(target=internet.update_price_change, args=(country, copy.deepcopy(stk['bscs']['symbol']), core, None)).start()
                else:
                    if not index:
                        DB.update_field(collection, symbol, "ignore", "YES")
                        #DB.update_field(collection, symbol, "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))
                        DB.update_price_failcount(stk, country, df=True)

                #if index:
                #    df = update_percent_change(df)
                #Update Betas
                #if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
                #    df = hdf_get_beta(country, symbol, df)
                #    #DB.update_stock_betas2(country, stk, df=df)
                #if not df.empty:
                #if True:
                #    ##write_to_hdf(country, df, symbol)
                #    # Update the date on which the price is updated
                #    DB.update_field(collection, symbol, "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))
                #    #DB.update_field(collection, symbol, "ignore", "NO")
        #Updating today's price and volume
        else:
            ##if index:
            #if True:
            #    # Yahoo Finance sometimes returns wrong volume data for the latest date.
            #    # Check and delete record.
            #    # Will be populated again the below code.
            #    # Happens only when small set of data is requested.
            #    DB.check_volume_of_last_record(sql_engine, DB.get_symbol_table_name(stk['bscs']['symbol']))
            #else:
            #    pass
            #    #last_updated_date = dt.strptime(stk['dates']['mysql_price_date'].split(' ')[0], "%Y-%m-%d").date()
            #    #if last_updated_date >= end:
            #    #    return

            failcount = 0
            if 'failcount' in stk.keys() and \
                    'mysql_price_failcount' in stk['failcount'].keys():

                    failcount = stk['failcount']['mysql_price_failcount']
                    if stk['failcount']['mysql_price_failcount'] > MAX_FAIL_COUNT:
                        return

            if not DB.mysql_exists_table(sql_engine, table):
                rdf = pd.DataFrame()
            else:
                table_name = DB.get_symbol_table_name(stk['bscs']['symbol'])
                columns = DB.mysql_get_columns_from_engine(sql_engine, table_name)
                if 'Adj Close' not in columns:
                    rdf = pd.DataFrame()
                else:

                    # The tables with the same symbol name might have been
                    # pre-existing and the new entries are appended to the old entries.
                    # Or might have wrong data due to code errors.
                    # So, truncate the whole table and repopulate the entries.
                    # From now for all the new symbols that are added, this step is added
                    # in add_symbol_to_database(d, db)
                    if True:
                    #if check_since_ipo_date:
                        if 'since' in stk['bscs'].keys() \
                                and stk['bscs']['since'] is not None:
                                #and date.today().year == stk['bscs']['since'].year:
                            # Truncate the whole table, pull the new prices and recreate the percentage changes.
                            if DB.mysql_exists_table(sql_engine, table_name):

                                query = 'select Date, `Adj Close` from {} order by Date asc limit 1'.format(table_name)
                                df = DB.read_from_sql(query, sql_engine)
                                # The table has old entries. Remove those entries
                                try:
                                    if not df.empty and\
                                        stk['bscs']['since'] and\
                                        'price_truncate_date' not in stk['bscs'].keys() and \
                                        abs((stk['bscs']['since'] - df.index[0]).days) >= 7: # If atleast there's a time difference of 7 days between the IPO date and the start index date, truncate them and repopulate again.
                                        print("%s: Old entries in price table, IPO Date: %r, first row date: %r deleting" %(stk['bscs']['symbol'], str(stk['bscs']['since']), str(df.index[0])))
                                        if  stk['bscs']['since'] > df.index[0]:
                                            cols = DB.mysql_get_columns(table_name, sql_engine)
                                            if 'Day Change' in cols:
                                                query = "update {} set `Day Change`=NULL, `Week Change`=NULL, `Two Week Change`=NULL, `Month Change`=NULL, `Quarter Change`=NULL, `Half Year Change`=NULL, `Year Change`=NULL, `Five Year Change`=NULL, `Whole Change`=NULL".format(table_name)
                                                sql_engine.execute(query)
                                            query = "delete from {} where Date < %r".format(table_name)%(str(stk['bscs']['since'].date()))
                                            sql_engine.execute(query)
                                            DB.update_field(collection, symbol, "bscs.price_truncate_date", dt.combine(dt.now(), dt.min.time())) 
                                        else:
                                            query = "drop table {}".format(table_name)
                                            sql_engine.execute(query)
                                            DB.mysql_check_n_create_table(sql_engine, table_name, unknown_table=False, primary_key=True, empty_table=False, fin_table=False)
                                            DB.update_field(collection, symbol, "bscs.price_truncate_date", dt.combine(dt.now(), dt.min.time())) 
                                        beta_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Beta')
                                        # Truncate betas.
                                        if DB.mysql_exists_table(beta_engine, table_name):
                                            query = "drop table {}".format(table_name)
                                            beta_engine.execute(query)
                                            DB.mysql_check_n_create_table(beta_engine, table_name, unknown_table=False, primary_key=True, empty_table=False, fin_table=False)
                                        DB.close_sql_connection(beta_engine)
                                except Exception as E:
                                    print ("%s: Error during price truncate checking" %(stk['bscs']['symbol']))
                                    print(str(E))
        
                    query = 'select Date from ' + table + ' order by Date DESC limit 1'
                    #rdf = read_from_hdf(country, symbol)
                    rdf = DB.read_from_sql(query, sql_engine)
                    #rdf = DB.read_from_sql2(sql_engine, table, ['Date'], order='desc', limit=1)

            # Read the existing data of the symbol
            #rdf = read_from_hdf(country, symbol)
            #rdf = read_from_hdf_store(country, stk['bscs']['symbol'])
            if rdf.empty:
                #PRINT_ERR("update_dataframe_price_volume: Couldnt read %r" %(stk['bscs']['symbol']))
                start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
            else:
                #get timestamp of the last entry
                #start = rdf.index[-1].date()
                start = dt.strptime(rdf['Date'][0], "%Y-%m-%d").date()
            #get data from next date till today
            #print("one: sym: %r, start: %r, end: %r" %(stk['bscs']['symbol'], str(start), str(end)))
            if start < end:
            #if True:
                # If date difference is less than a week, get atleast
                # a week of prices. yahoofinance sometimes misbehaves
                # in case of a shorter timespan and returns inconsistent data.
                # Min of week is a safer timespan.
                # Though you get a week data, insert only the entries that are missing.
                # Taken care below.
                #if end-start < timedelta(10):
                #    start = end - timedelta(10)

                print("getting data for %r , sno: %r" %(stk['bscs']['symbol'], stk['sno']))
                #s=time.time()
                df = get_stock_data(country, stk, start, end, vpn_event, eod_token=eod_token)
                data_pull = True
                # Sometimes yahoo gives wrong data. Wrong data will have volume as 0. Discard those rows
                if df is not None and 'Volume' in df.columns:
                    df.drop(df[df['Volume']==0].index, inplace=True)
                #e=time.time()
                #print("got data for %r from yahoo, elapsed time: %r sec" %(stk['bscs']['symbol'], (e-s)))
                #print("two: sym: %r, start: %r, end: %r" %(stk['bscs']['symbol'], str(start), str(end)))
                if df is not None and not df.empty:
                    xdf=copy.deepcopy(df)
                    #rdf = rdf.append(df)
                    #rdf = remove_df_duplicates(rdf)
                    #df['Symbol'] = symbol
                    df['Date'] = df.index.strftime("%Y-%m-%d")
                    df.index = df['Date'] #Is it required?
                    #df = df[~df.Date.isin(rdf.Date)]
                    # Get the data starting from the next day of the last entry in MySQL database
                    #df=df.loc[rdf['Date'][0]:].drop(rdf['Date'][0])
                    if not df.empty:
                        try:
                            if not rdf.empty and rdf['Date'][0] in list(df.index):
                                df_index = df.index.get_loc(rdf['Date'][0])
                                df = df[df_index+1:]
                        except Exception as E:
                            print("hdf5.py: %r: update_dataframe_price_volume exception: %r"%(symbol, str(E)))
                            print("hdf5.py: %r: update_dataframe_price_volume exception, df: %r"%(symbol, df))
                            print("hdf5.py: %r: update_dataframe_price_volume exception, xdf: %r"%(symbol, xdf))
                            print("hdf5.py: %r: update_dataframe_price_volume exception, rdf: %r"%(symbol, rdf))
                    if not df.empty:
                        #print("Writing to sql prices for %r" %(symbol))
                        #print("writing data for %r to mysql" %(stk['bscs']['symbol']))
                        #s=time.time()
                        #DB.write_to_sql(sql_engine, table, df)
                        DB.mysql_update_table(sql_engine, table, df, insert=True, check=True, date_column=False, format_columns=False)
                        #DB.update_field(collection, symbol, "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))
                        # Reset mysql_price_failcount
                        if not index:
                            DB.update_field(collection, symbol, "price_change.price", df['Adj Close'][-1])
                            DB.update_field(collection, symbol, "failcount.mysql_price_failcount", 0)
                            DB.update_field(collection, symbol, "price_change.volume", df['Volume'][-1])
                        else:
                            DB.update_field(collection, stk['bscs']['symbol'], "price_change.price", df['Adj Close'][-1])
                        data_update = True

                        if percent_change:
                            multiprocessing.Process(target=internet.update_price_change, args=(country, copy.deepcopy(stk['bscs']['symbol']), core, None)).start()
                        #threading.Thread(target=internet.update_price_change, args=(country, collection, stk['bscs']['symbol'], None, sql_engine,)).start()
                        #e=time.time()
                        #print("done data for %r to mysql, elapsed time: %r sec" %(stk['bscs']['symbol'], (e-s)))
                        #print("Wrote to sql prices for %r" %(symbol))
 
                    ##if index:
                    ##    rdf = update_percent_change(rdf)
                    ##Update Betas
                    ##if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
                    ##    rdf = hdf_get_beta(country, symbol, rdf)
                    ##    #DB.update_stock_betas2(country, stk, df=rdf)
                    #write_to_hdf(country, rdf, symbol)
                    #write_to_hdf_store(country, rdf, stk['bscs']['symbol'])
                    # Update the date on which the price is updated
                    #DB.update_field(collection, symbol, "ignore", "NO")
                #else:
                if df.empty:
                    if not index:
                        PRINT_ERR("df empty for %r" %(symbol))
                        DB.update_field(collection, symbol, "ignore", "YES")
                        #DB.update_field(collection, symbol, "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))
                        DB.update_price_failcount(stk, country, df=True)

                if not index:
                    if data_pull:
                        if df is not None and not df.empty:
                            DB.update_field(collection, symbol, "dates.mysql_price_date", dt.strptime(df.index[-1], "%Y-%m-%d"))
                        DB.update_field(collection, symbol, "dates.mysql_price_pull_date", dt.combine(dt.now(), dt.min.time()))
                    else:
                        DB.update_price_failcount(stk, country, df=True)
                        #failcount = failcount + 1
                        #print("%s: Updating %r for field failcount.mysql_price_failcount" %(stk['bscs']['symbol'], failcount))
                        #DB.update_field(collection, symbol, "failcount.mysql_price_failcount", failcount)
                    if data_update:
                        DB.update_field(collection, symbol, "dates.mysql_price_pull_success", True)
                    else:
                        DB.update_field(collection, symbol, "dates.mysql_price_pull_success", False)

    finally:
        # Update the date on which the price is updated
        if local_mdb:
            DB.close_db_client(c)
        if local_sql:
            DB.close_sql_connection(sql_engine)
        if sem:
            sem.release()
