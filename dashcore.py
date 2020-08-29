import DB
import hdf5

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import dash_elasticsearch_autosuggest as dea

import plotly.express as px
import plotly.graph_objs as go

from datetime import date, timedelta, datetime as dt
import pandas as pd
import pprint
import pandas_ta as ta
import numpy as np
import copy

class DashBoard:
    def __init__(self, symbol=None):
        self.stock  = DashStock(symbol)
        self.com = {}
        self.com['sym'] = {}
        self.com['sym']['input']  = 'input-box'
        self.com['sym']['suggest']= 'suggest-syms'
        self.com['sym']['button'] = 'button'
        self.fig = None
        self.p_graph_id = 'price-graph'
        self.p_graph = {}
        self.p_graph_prop = {}
        self.p_graph_prop['line'] ={} 
        self.p_graph_prop['sell'] ={} 
        self.p_graph_prop['buy'] ={} 
        self.p_graph_prop['buy_sma'] ={} 
        self.p_graph_prop['sell_sma'] ={}

        self.app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.LITERA])
        self.create_layout()

    #@property
    #def p_graph_id(self):
    #    return self._p_graph_id


    def create_layout(self):
        self.app.layout = html.Div(children=[
            html.H1(children='Stock Prices'),
        
            html.Div(children='''
                Dash: A web application framework for Python.
            '''),
            html.Datalist(
                id=self.com['sym']['suggest'], 
                children=[html.Option(value=word) 
                            for word in DB.get_symbols_from_mongo()]
            ),
            dcc.Input(id=self.com['sym']['input'],
                type='text',
                list=self.com['sym']['suggest'],
                placeholder='Enter a Stock Symbol',
                value=''
            ),
        
            html.Button('Submit', id=self.com['sym']['button']),
        
            dcc.Graph(
                id=self.p_graph_id,
                animate=True
                #style={'backgroundColor':'#1a2d46', 'color':'#ffffff'},
                )
        
        ])

class DashStock:
    def __init__(self, symbol=None):
        self.df     = pd.DataFrame()
        self.data   = {}
        self._symbol = symbol

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

    # Read stock data from the database
    def populate(self):
        columns = ['Date', 
                   'Open', 
                   'Low', 
                   'Close',
                   'Adj Close'
                ]
        self.df  = DB.get_stock_prices(self.symbol, columns=columns)
        self.df['SMA30']  = self.df['Adj Close'].rolling(window=30).mean()
        self.df['SMA100'] = self.df['Adj Close'].rolling(window=100).mean()
        self.df['RSI']    = ta.rsi(self.df['Adj Close'])
        self.update_sma_buy_sell()
        self.data = DB.read_stock_from_mongo(self.symbol)

def get_start_end(df, points):
    # Return None for 'autosize', 'xaxis.autorange', None
    start = end = None

    if points:
        keys = points.keys()

        if len(keys) == 1 and 'yaxis.range' in keys:
            #start = df[df['Adj Close'] == points['yaxis.range'][0]].index[0]
            start = df.iloc[(df['Adj Close']-points['yaxis.range'][0]).abs().argsort()[:2]].index[0]
            end   = df.index[-1]
        if 'xaxis.range' in keys:
            start = points['xaxis.range'][0].split(' ')[0].split('T')[0]
            end   = points['xaxis.range'][1].split(' ')[0].split('T')[0]
        elif 'xaxis.range[0]' in keys:
            start = points['xaxis.range[0]'].split(' ')[0].split('T')[0]
            end   = points['xaxis.range[1]'].split(' ')[0].split('T')[0]
    #print("Start: %r, End: %r" %(start, end))
    return start, end 

