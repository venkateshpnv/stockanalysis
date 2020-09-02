import pandas_datareader
import datetime

import pandas_datareader as pdr
from pandas_datareader.quandl import QuandlReader


START = datetime.datetime(2019, 4, 1)
END = datetime.datetime(2019, 4, 30)

def get_data(ticker):
        #df = pandas_datareader.data.DataReader('%s' % (ticker), 'morningstar', start, end, retry_count=0)
    try:
        #data = QuandlReader("WIKI/{}".format(ticker), start=START, end=END)
        #df = data.read()
        #df = pandas_datareader.data.DataReader("^SNX", 'stooq', START, END)
        df = pandas_datareader.data.DataReader("BWL-A", 'yahoo', START, END)
        #df = pdr.DataReader(ticker, 'iex', START, END)
        print(df.tail(5))
    except ValueError:
        print('Ticker Symbol %s is not available!' % (ticker))

get_data('TSLA') #valid Symbol
#get_data('yyfy') #not a valid Symbol
