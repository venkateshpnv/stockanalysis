import pandas as pd
import pandas_datareader as pdr
import h5py
from datetime import date, timedelta, datetime as dt
from common import *
import time
from dateutil.relativedelta import relativedelta
import DB
import os

#hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/US_price_data.hd5'
hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/test.h5'
US_hdf_store_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/hdf_store.h5'
India_hdf_store_path='/home/vpetla/work/stockanalysis/India_Stocks/DCF_Calc/hdf_store.h5'

def get_stock_data(country, symbol, start, end):
    try:
        if country == 'India':
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
 
def hdf_replace_dataset(hdf_path, symbol, rdf, lock):
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

def get_symbols_hdf_store(country, lock):
    symbols = []
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            symbols = store.keys()
    finally:
        lock.release()
    return symbols

def write_to_hdf_store(country, df, symbol, lock):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            store[symbol] = df
    finally:
        lock.release()

def read_from_hdf_store(country, symbol, lock):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
            df = store[symbol]
    except Exception as e:
        print(str(e))
        return pd.DataFrame()
    finally:
        lock.release()
    return df

def read_from_hdf_store_nolock(country, symbol):
    path = get_hdf_store_path(country)
    with pd.HDFStore(path, mode='a', complevel=9, complib='bzip2') as store:
        df = store[symbol]
    return df

def write_to_hdf(country, df, symbol, lock):
    try:
        path = get_hdf_store_path(country)
        lock.acquire()
        df.to_hdf(path, key=symbol, mode='a', format='table', append=True, complevel=9, complib='zlib')
    finally:
        lock.release()

def read_from_hdf(country, symbol, lock):
    try:
        lock.acquire()
        path = get_hdf_store_path(country)
        rdf  = pd.read_hdf(path, symbol)
    finally:
        lock.release()
    return rdf

def get_dataframe(country, sym):
    path = get_hdf_store_path(country)
    return pd.read_hdf(path, sym)

def hdf_price_change(country, sym, df, num_days):
    en_price = hdf_get_price(sym, df, dt.now().date())
    st_price = hdf_get_price(sym, df, dt.now().date() - relativedelta(days=num_days))
    if st_price == 0:
        return 0
    return (en_price/st_price - 1)

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
 
def update_dataframe_price_volume(country, db, symbols, stk, sem, lock):
    if stk is None:
        print("hdf5: stk none, skipping %s: %s" %(stk['bscs']['symbol'], stk['bscs']['name']))
        sem.release()
        return

    df=pd.DataFrame() 
    collection = DB.get_collection(country, db)
    try:
        today=str(dt.now().date())
        end=dt.now().date()#-timedelta(2)
        #Updating the price and volume for the first time
        symbol = '/' + stk['bscs']['symbol']
        if symbol not in symbols:
            #print("%r : symbol not preset getting full data" %(stk['bscs']['symbol']))
            since = "1970-01-01"
            start = dt.strptime(since, "%Y-%m-%d").date()
            df = get_stock_data(country, stk['bscs']['symbol'].replace('.','-'), start, end)
            if not df.empty:
                write_to_hdf_store(country, df, stk['bscs']['symbol'], lock)
                # Update the date on which the price is updated
                DB.update_field(collection, stk['bscs']['symbol'], "bscs.price_date", today)
                #print("hdf5: Done: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
        #Updating today's price and volume
        else:
            # Read the existing data of the symbol
            rdf = read_from_hdf_store(country, stk['bscs']['symbol'], lock)
            if rdf.empty:
                PRINT_ERR("Couldnt read %r from %r" %(stk['bscs']['symbol'], hdf_path))
                sem.release()
                return
            #get timestamp of the last entry
            start = rdf.index[-1].date()
            #get data from next date till today
            #print("one: sym: %r, start: %r, end: %r" %(stk['bscs']['symbol'], str(start), str(end)))
            if start < end:
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
                    rdf = rdf.sort_index()
                    #rdf = rdf.drop_duplicates()
                    rdf=rdf[~rdf.index.duplicated(keep='last')]
                    write_to_hdf_store(country, rdf, stk['bscs']['symbol'], lock)
                    #print(stk['bscs']['symbol'], rdf.tail(5))
                    # Update the date on which the price is updated
                    DB.update_field(collection, stk['bscs']['symbol'], "bscs.price_date", today)
                    #print("hdf5: Done: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
    except Exception as E:
        print("hdf5: update_dataframe_price_volume:",str(E))
    finally:
        sem.release()
