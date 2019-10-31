import pandas as pd
import pandas_datareader as pdr
import h5py
from datetime import date, timedelta, datetime as dt
from common import *
import time
from dateutil.relativedelta import relativedelta
import DB
import os

hdf_path='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/US_price_data.hd5'

def get_stock_data(symbol, start, end):
    try:
        df = pdr.DataReader(symbol,'yahoo',start, end, retry_count=3)
        df = df.astype('float64')
    except Exception as E:
        PRINT_ERR(str(E))
        return pd.DataFrame()
    return df

def write_to_hdf(hdf_path, df, symbol, lock):
    lock.acquire()
    df.to_hdf(hdf_path, key=symbol, mode='a', format='table', append=True, complevel=9, complib='bzip2')
    lock.release()

def read_from_hdf(hdf_path, symbol, lock):
    lock.acquire()
    rdf = pd.read_hdf(hdf_path, symbol)
    lock.release()
    return rdf

def get_dataframe(country, sym):
    return pd.read_hdf(hdf_path, sym)

def hdf_price_change(sym, df, num_days):
    en_price = hdf_get_price(sym, df, dt.now().date() - relativedelta(days=1))
    st_price = hdf_get_price(sym, df, dt.now().date() - relativedelta(days=num_days+1))
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
 
def update_dataframe_price_volume(db, stk, sem, lock):
    print("hdf5: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
    df=pd.DataFrame() 
    try:
        lock.acquire()
        if not os.path.exists(hdf_path):
            f=h5py.File(hdf_path, 'x')
            f.close()

        f=h5py.File(hdf_path, 'r')
        if f is None:
            PRINT_ERR("Unable to open %r" %(hdf_path))
            lock.release()
            print("hdf5: file error, skipping %s: %s" %(stk['bscs']['symbol'], stk['bscs']['name']))
            return
        symbols = list(f.keys())
        f.close()
        lock.release()

        if stk is None:
            print("hdf5: stk none, skipping %s: %s" %(stk['bscs']['symbol'], stk['bscs']['name']))
            return

        today=str(dt.now().date())
        end=dt.now().date()
        if stk['bscs']['symbol'] == 'UI':
            print("****************** Getting data for UI **********************")
        #Updating the price and volume for the first time
        if stk['bscs']['symbol'] not in symbols:
            #if not 'since' in stk['bscs'].keys():
            #    PRINT_ERR("Since not present in %r" %(stk['bscs']['symbol']))
            #    since = "1970-01-01"
            #else:
            #    since = stk['bscs']['since']
            since = "1970-01-01"
            start = dt.strptime(since, "%Y-%m-%d").date()
            df = get_stock_data(stk['bscs']['symbol'].replace('.','-'), start, end)
            if not df.empty:
                write_to_hdf(hdf_path, df, stk['bscs']['symbol'], lock)
                # Update the date on which the price is updated
                DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.price_date", today)
                print("hdf5: Done: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
        #Updating today's price and volume
        else:
            # Read the existing data of the symbol
            rdf = read_from_hdf(hdf_path, stk['bscs']['symbol'], lock)
            #get timestamp of the last entry
            start = rdf.index[-1].date() + timedelta(1)
            #get data from next date till today
            if start <= end:
                df = get_stock_data(stk['bscs']['symbol'].replace('.','-'), start, end)
                print("sym: %r, start: %r, end: %r" %(stk['bscs']['symbol'], str(start), str(end)))
                #print(str(start), str(end), symbol, df)
                # df should not be empty.
                # sometimes, the df has entries older than the last entry in hdf5.
                # if so, ignore them.
                if not df.empty:
                    if stk['bscs']['symbol'] == 'VISI':
                        print(stk['bscs']['symbol'], df.index[0], rdf.index[-1])
                    for i in df.index:
                        if i not in rdf.index:
                            write_to_hdf(hdf_path, df.loc[i], stk['bscs']['symbol'], lock)
                    # Update the date on which the price is updated
                    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.price_date", today)
                    print("hdf5: Done: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
    except Exception as E:
        print("hdf5: update_dataframe_price_volume:",str(E))
    finally:
        sem.release()

##start = "2000-01-01"
##end = "2018-01-01"
##start = "2018-01-02"
##end = "2019-01-01"
#start = "2019-01-02"
#end = "2019-10-17"
#
#
#st_date = dt.strptime(start, "%Y-%m-%d").date()
#end_date = dt.strptime(end, "%Y-%m-%d").date()
#
#symbol = 'AAPL'
#df = get_stock_data(symbol, start, end)
#write_to_hdf(hdf_path, df, symbol)
#
#df = get_stock_data('PG', start, end)
#df.to_hdf(hdf_path, key='PG', mode='a', format='table', append=True, complevel=9, complib='bzip2')
#
#df = get_stock_data('MSFT', start, end)
#df.to_hdf(hdf_path, key='MSFT', mode='a', format='table', append=True, complevel=9, complib='bzip2'
#
#df = get_stock_data('IBM', start, end)
#df.to_hdf(hdf_path, key='IBM', mode='a', format='table', append=True, complevel=9, complib='bzip2')
#rdf=pd.read_hdf('/tmp/US_Stocks.hd5', 'AAPL')
#print(rdf.loc['2019-10-06 00:00:00':'2019-10-17 00:00:00'])
#dates = rdf.index
#print(rdf.loc[list(dates)[0]:list(dates[10])])
