import pandas as pd
import pandas_datareader as pdr
import h5py
from datetime import date, timedelta, datetime as dt
from common import *
from datastructures import *
import time
from dateutil.relativedelta import relativedelta
from pandas.tseries.holiday import get_calendar
import sqlalchemy

import DB
import os
from arctic import Arctic
import threading

#hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/US_price_data.hd5'
hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/test.h5'
US_hdf_store_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/hdf_store2.h5'
India_hdf_store_path='/home/vpetla/work/stockanalysis/India_Stocks/DCF_Calc/hdf_store2.h5'

lock = threading.Lock()
US_Cal = get_calendar('USFederalHolidayCalendar')

def get_stock_data(country, symbol, start, end):
    try:
        if country == 'India' and symbol not in India_indices.keys():
            symbol = symbol + '.BO'
        df = pdr.DataReader(symbol,'yahoo',start, end, retry_count=5)
        df = df.astype('float64')
    except Exception as E:
        PRINT_ERR(str(E))
        return pd.DataFrame()
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

def read_from_hdf(country, symbol):
    rdf=pd.DataFrame() 
    try:
        lock.acquire()
        path = get_hdf_store_path(country)
        rdf  = pd.read_hdf(path, symbol)
    except Exception as e:
        print("read_from_hdf(): symbol: %r, error: %r" %(symbol, str(e)))
    finally:
        lock.release()
    return rdf

def write_to_hdf(country, df, symbol):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with h5py.File(path, 'a') as f:
            symbols=list(f.keys())
            if symbol in symbols:
                del f[symbol]
        df.to_hdf(path, key=symbol, mode='a', format='table', append=True, complevel=9, complib='zlib')
    except Exception as e:
        f.close()
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
        df = get_dataframe(country, sym)
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
        print("no args, take from start")
        #Price Change since beginning
        since = DB.get_since(country, sym)
        start = dt.strptime(since, "%Y-%m-%d").date()
 
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
def get_nearest_index(df, req_date):
    return df.index.get_loc(req_date, method='nearest')
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
    df = get_dataframe(country, sym)
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
 
def update_dataframe_price_volume(country, db, symbols, stk, sem):
    if stk is None:
        print("hdf5: stk none, skipping %s: %s" %(stk['bscs']['symbol'], stk['bscs']['name']))
        sem.release()
        return
    if country == 'India':
        indices = India_indices
    else:
        indices = US_indices 
 
    df=pd.DataFrame() 
    collection = DB.get_collection(country, db)
    try:
        today=str(dt.now())
        end=dt.now().date()# - timedelta(7)
        #Updating the price and volume for the first time
        if stk['bscs']['symbol'] in indices.keys():
            symbol = indices[stk['bscs']['symbol']]
        else:
            symbol = stk['bscs']['symbol']
        #symbol = '/' + stk['bscs']['symbol']

        if symbol not in symbols:
            start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
            df = get_stock_data(country, stk['bscs']['symbol'].replace('.','-'), start, end)
            df = remove_df_duplicates(df)
            #Update Betas
            #if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
            #    DB.update_stock_betas2(country, stk, df=df)
            #if not df.empty:
            if True:
                write_to_hdf(country, df, symbol)
                # Update the date on which the price is updated
                DB.update_field(collection, symbol, "bscs.price_date", today)
        #Updating today's price and volume
        else:
            # Read the existing data of the symbol
            rdf = read_from_hdf(country, symbol)
            #rdf = read_from_hdf_store(country, stk['bscs']['symbol'])
            if rdf.empty:
                PRINT_ERR("update_dataframe_price_volume: Couldnt read %r" %(stk['bscs']['symbol']))
                start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
            else:
                #get timestamp of the last entry
                start = rdf.index[-1].date()
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
                if end-start < timedelta(7):
                    start = end - timedelta(7)

                df = get_stock_data(country, stk['bscs']['symbol'].replace('.','-'), start, end)
                #print("two: sym: %r, start: %r, end: %r" %(stk['bscs']['symbol'], str(start), str(end)))
                if not df.empty:
                    rdf = rdf.append(df)
                    rdf = remove_df_duplicates(rdf)
                   #Update Betas
                    #if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
                    #    DB.update_stock_betas2(country, stk, df=rdf)
                    write_to_hdf(country, rdf, symbol)
                    #write_to_hdf_store(country, rdf, stk['bscs']['symbol'])
                    # Update the date on which the price is updated
                    DB.update_field(collection, symbol, "bscs.price_date", today)
                else:
                    PRINT_ERR("df empty for %r" %(symbol))
    except Exception as E:
        print("hdf5: update_dataframe_price_volume:",str(E))
    finally:
        sem.release()
