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
from math import nan, isnan
import numpy as np
import copy

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
            df = get_dataframe(country, sym)
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
            dfb = get_dataframe(country, bindex, df.index[0], df.index[-1])
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

        df.loc[i][field] = change
    return df

# Update df daily, weekly etc percent change
def update_percent_change(df):
    fields = ['Day Change', 'Week Change', 'Month Change', 'Quarter Change', 'Half Year Change', 'Year Change', 'Five Year Change', 'Ten Year Change', 'Whole Change']
    durations = [relativedelta(days=1), relativedelta(weeks=1), relativedelta(months=1), relativedelta(months=3), relativedelta(months=6), relativedelta(years=1), relativedelta(years=5), relativedelta(years=10)]
 
    write = False
    for f in fields:
        if f not in list(df.keys()):
            df[f] = nan

    for i in range(len(durations)):
        # Get all rows where the '%s Change' is empty
        #nans=df.index[isnan(df[fields[i]])]
        #nans = df[1:].index[df[fields[i]].isnull()]
        is_nan=df[fields[i]].isnull()
        nans = (df[1:])[is_nan]
        if not nans.empty:
            print("Field %r" %(fields[i]))
            df = update_field_change(df, nans.index, fields[i], durations[i])
            write = True

    # Same logic but for "Whole Change" field
    is_nan=df[fields[-1]].isnull()
    nans = (df[1:])[is_nan].index
    if len(nans) > 0:
        print("Field %r" %(fields[-1]))
        df = update_field_change(df, nans, fields[-1], 0, whole_change=True)
        write = True

    return df, write

# Update day change, week change, month change etc till 10 year and whole percent change in the price of the stock for every day and update it in the df
def update_percent_change_all(country):
    mysql_engine = DB.open_sql_connection('10.0.0.12', 'root', 'petla123', 3036, 'US_Stocks')
    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection(country, db)
    stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
 
    try:
        i = 1
        for stk in stocks:
            if i < 574: #Skipped 574 STKCLF
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
                    DB.check_n_write_to_sql(mysql_engine, symbol, copy.deepcopy(df))
            i = i + 1
    finally:
        DB.close_db_client(c)
        DB.close_sql_connection(mysql_engine)

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
            index  = True
            symbol = indices[stk['bscs']['symbol']]
        else:
            index  = False
            symbol = stk['bscs']['symbol']
        #symbol = '/' + stk['bscs']['symbol']

        if symbol not in symbols:
            start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
            df = get_stock_data(country, stk['bscs']['symbol'].replace('.','-'), start, end)
            df = remove_df_duplicates(df)
            #if index:
            #    df = update_percent_change(df)
            #Update Betas
            #if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
            #    df = hdf_get_beta(country, symbol, df)
            #    #DB.update_stock_betas2(country, stk, df=df)
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
                    #if index:
                    #    rdf = update_percent_change(rdf)
                    #Update Betas
                    #if stk['bscs']['symbol'] not in India_indices.keys() and stk['bscs']['symbol'] not in US_indices.keys():
                    #    rdf = hdf_get_beta(country, symbol, rdf)
                    #    #DB.update_stock_betas2(country, stk, df=rdf)
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
