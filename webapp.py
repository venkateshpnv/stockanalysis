import streamlit as st
from datetime import date, timedelta, datetime as dt
from dateutil.relativedelta import relativedelta
import yfinance as yf
#from fbprophet import Prophet
#from fbprophet.plot import plot_plotly
from plotly import graph_objs as go
from plotly.subplots import make_subplots
from DB import *
import pandas as pd
import pandas_ta as ta
import talib
import hdf5
import cufflinks as cf
import pandas as pd

class Market:
    def __init__(self):
        self.bond_yields = pd.DataFrame()

    def populate_bond_yields(self, mysql_engine=None):
        local_mysql_engine = False
        if not mysql_engine:
            local_mysql_engine = True
            mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Data')

        query = 'select * from {}'.format('BOND_YIELDS')
        self.bond_yields = read_from_sql(query, mysql_engine)

        if local_mysql_engine:
            close_sql_connection(mysql_engine)

class Stock:
    def __init__(self, symbol=None):
        self.df     = pd.DataFrame()
        #self.RSI    = pd.DataFrame()
        #self.PSAR   = pd.DataFrame()
        #self.EMA    = pd.DataFrame()
        #self.MFI    = pd.DataFrame()
        #self.MACD   = pd.DataFrame()
        #self.BBANDS = pd.DataFrame()
        # All mongodb data
        self.data   = {}
        self._symbol = symbol
        self.fin = {}
        self.fin['balance_sheet'] = {}
        self.fin['balance_sheet']['yearly']    = pd.DataFrame()
        self.fin['balance_sheet']['quarterly'] = pd.DataFrame()
        self.fin['income_statement'] = {}
        self.fin['income_statement']['yearly']    = pd.DataFrame()
        self.fin['income_statement']['quarterly'] = pd.DataFrame()
        self.fin['cashflow_statement'] = {}
        self.fin['cashflow_statement']['yearly']    = pd.DataFrame()
        self.fin['cashflow_statement']['quarterly'] = pd.DataFrame()
        self.fin['earnings'] = pd.DataFrame()
        self.fin['splits'] = pd.DataFrame()
        self.fin['dividends'] = pd.DataFrame()
        self.short_interests = pd.DataFrame()
        self.put_call_ratios = pd.DataFrame()
        self.technicals = pd.DataFrame()

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, sym):
        if sym:
            self._symbol = sym
            print("************* Populating data")
            self.populate()

    def update_sma_buy_sell(self):
        flag = -1
        buy  = []
        sell = []
    
        idx = 0
        for i, d in self.df.iterrows():
            if d['SMA30'] < d['SMA100']:
                if flag != 1:
                    buy.append(d['Adj Close'])
                    sell.append(np.nan)
                    flag = 1
                else:
                    buy.append(np.nan)
                    sell.append(np.nan)
            elif d['SMA30'] > d['SMA100']:
                if flag != 0:
                    buy.append(np.nan)
                    sell.append(d['Adj Close'])
                    flag = 0
                else:
                    buy.append(np.nan)
                    sell.append(np.nan)
            else:
                buy.append(np.nan)
                sell.append(np.nan)
            idx = idx + 1
        self.df['SMA_Buy']  = buy
        self.df['SMA_Sell'] = sell

    def populate_all(self):
        self.populate_financials()
        self.populate_short_interests()
        self.populate_put_call_ratios()
        self.populate_technicals()

    # Get financial statements and other information
    def populate_financials(self, mysql_engine=None):
        local_mysql_engine = False
        if not mysql_engine:
            local_mysql_engine = True
            mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')

        query = 'select * from {} where Symbol = \'{}\''.format('Balance_Sheet_yearly', self.symbol)
        self.fin['balance_sheet']['yearly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Balance_Sheet_quarterly', self.symbol)
        self.fin['balance_sheet']['quarterly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Income_Statement_yearly', self.symbol)
        self.fin['income_statement']['yearly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Income_Statement_quarterly', self.symbol)
        self.fin['income_statement']['quarterly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Cash_Flow_yearly', self.symbol)
        self.fin['cashflow_statement']['yearly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Cash_Flow_quarterly', self.symbol)
        self.fin['cashflow_statement']['quarterly']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Earnings_History', self.symbol)
        self.fin['earnings']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Splits_History', self.symbol)
        self.fin['splits']= read_from_sql(query, mysql_engine)
        
        query = 'select * from {} where Symbol = \'{}\''.format('Dividends_History', self.symbol)
        self.fin['dividends']= read_from_sql(query, mysql_engine)

        if local_mysql_engine:
            close_sql_connection(mysql_engine)

    # Get short interests
    def populate_short_interests(self, mysql_engine=None):
        local_mysql_engine = False
        if not mysql_engine:
            local_mysql_engine = True
            mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Short_Interests')

        query = 'select * from {}'.format(get_symbol_table_name(self.symbol))
        self.short_interests = read_from_sql(query, mysql_engine)

        if local_mysql_engine:
            close_sql_connection(mysql_engine)

    # Get put/call ratio
    def populate_put_call_ratios(self, mysql_engine=None):
        local_mysql_engine = False
        if not mysql_engine:
            local_mysql_engine = True
            mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Options')

        query = 'select * from {}'.format(get_symbol_table_name(self.symbol))
        self.put_call_ratios = read_from_sql(query, mysql_engine)

        if local_mysql_engine:
            close_sql_connection(mysql_engine)

    # Get technicals
    def populate_technicals(self, mysql_engine=None):
        local_mysql_engine = False
        if not mysql_engine:
            local_mysql_engine = True
            mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Technicals')

        query = 'select * from {}'.format(get_symbol_table_name(self.symbol))
        self.technicals = read_from_sql(query, mysql_engine)

        if local_mysql_engine:
            close_sql_connection(mysql_engine)

    # Read stock data from the database
    def populate(self):
        columns = ['Date', 
                   'Open', 
                   'Close',
                   'Low', 
                   'High', 
                   'Adj Close',
                   'Volume'
                ]
        self.df   = DB.get_stock_prices(self.symbol, columns=columns)
        self.data = DB.read_stock_from_mongo(self.symbol)

        self.df['SMA30']  = self.df['Adj Close'].rolling(window=30).mean()
        self.df['SMA100'] = self.df['Adj Close'].rolling(window=100).mean()
        self.df['RSI']    = ta.rsi(self.df['Adj Close'])
        self.df['MFI']    = ta.mfi(self.df['High'],
									self.df['Low'], 
									self.df['Adj Close'],
									self.df['Volume'], 
								  )
        self.df['MACD'], self.df['MACD_Hist'], self.df['MACD_Signal'] =  ta.macd(self.df['Adj Close'])
        self.df['BBANDS_Low'], self.df['BBANDS_Mid'], self.df['BBANDS_Upper'] = ta.bbands(self.df['Adj Close'])

        self.update_sma_buy_sell()
        self.populate_all()
        self.df.index = pd.to_datetime(self.df.index)

if __name__ == "__main__":
    today = dt.now()


