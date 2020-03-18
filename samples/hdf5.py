import pandas as pd
import pandas_datareader as pdr
import h5py
from datetime import date, timedelta, datetime as dt

def get_stock_data(symbol, start, end):
	df= pdr.DataReader(symbol,'yahoo',start, end, retry_count=3)
	df = df.astype('float64')
	return df

def write_to_hdf(hdf_path, df, symbol):
	df.to_hdf(hdf_path, key=symbol, mode='a', format='table', append=True, complevel=9, complib='bzip2')

#start = "2000-01-01"
#end = "2018-01-01"
#start = "2018-01-02"
#end = "2019-01-01"
start = "2019-01-02"
end = "2019-10-17"

#hdf_path='/tmp/US_Stocks.hd5'
hdf_path='/tmp/US_price_data.hd5'

st_date = dt.strptime(start, "%Y-%m-%d").date()
end_date = dt.strptime(end, "%Y-%m-%d").date()

symbol = 'AAPL'
df = get_stock_data(symbol, start, end)
write_to_hdf(hdf_path, df, symbol)

df = get_stock_data('PG', start, end)
df.to_hdf(hdf_path, key='PG', mode='a', format='table', append=True, complevel=9, complib='bzip2')

df = get_stock_data('MSFT', start, end)
df.to_hdf(hdf_path, key='MSFT', mode='a', format='table', append=True, complevel=9, complib='bzip2')

df = get_stock_data('IBM', start, end)
df.to_hdf(hdf_path, key='IBM', mode='a', format='table', append=True, complevel=9, complib='bzip2')
rdf=pd.read_hdf('/tmp/US_Stocks.hd5', 'AAPL')
print(rdf.loc['2019-10-06 00:00:00':'2019-10-17 00:00:00'])
dates = rdf.index
print(rdf.loc[list(dates)[0]:list(dates[10])])
