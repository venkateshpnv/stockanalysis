import DB
import hdf5

import dash
from dash import html
from dash import dcc
#import dash_core_components as dcc
#import dash_html_components as html
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
        self.symbol_info = ""
        self.p_graph_id = 'price-graph'
        self.p_graph = {}
        self.p_graph_prop = {}
        self.p_graph_prop['line'] ={} 
        self.p_graph_prop['rsi'] ={} 
        self.p_graph_prop['rsi_sell'] ={} 
        self.p_graph_prop['rsi_buy'] ={} 
        self.p_graph_prop['mfi'] ={} 
        self.p_graph_prop['mfi_sell'] ={} 
        self.p_graph_prop['mfi_buy'] ={} 
        self.p_graph_prop['sma_sell'] ={} 
        self.p_graph_prop['sma_buy'] ={}
        self.p_graph_prop['sma30'] ={} 
        self.p_graph_prop['sma100'] ={} 

        self.app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.LITERA])
        self.create_layout()

    #@property
    #def p_graph_id(self):
    #    return self._p_graph_id


    def create_layout(self):
        PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
       
        data_list =  html.Datalist(
                        id=self.com['sym']['suggest'], 
                        children=[html.Option(value=word) 
                            for word in DB.get_symbols_names_from_mongo()]
            )

        search_bar = dbc.Row(
            [
                dbc.Col(dbc.Input(id=self.com['sym']['input'], 
                                type="search",
                                list=self.com['sym']['suggest'],
                                placeholder="Enter a Stock Symbol",
                                size='30',
                                value=''
                )),
                dbc.Col(
                    dbc.Button("Search",
                               color="primary", 
                               className="ml-2",
                               id=self.com['sym']['button']
                              ),
                    width="auto",
                ),
            ],
            no_gutters=True,
            className="ml-auto flex-nowrap mt-3 mt-md-0",
            align="center",
        )
        navbar = dbc.Navbar(
            [
                html.Div(
                    # Use row and col to control vertical alignment of logo / brand
                    dbc.Row(
                        [
                            dbc.Col(html.Img(src=PLOTLY_LOGO, height="30px")),
                            dbc.Col(dbc.NavbarBrand("Stock Analyser", className="ml-2")),
                        ],
                        align="center",
                        no_gutters=True,
                    ),
                    #href="https://plot.ly",
                ),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse(search_bar, id="navbar-collapse", navbar=True),
            ],
            color="dark",
            dark=True,
        )

        symbol_info = dbc.Row(
                      [
                        html.H5(children="Symbol : AAPL", id='symbol-info'),
                        html.H5(children='Apple Computers Inc.', id='company-name'),
                      ],
                      align='left'
                     )
        price_info = dbc.Row(
                      [
                        html.H3(children="Price", id='symbol-price'),
                        html.H3(children='price change', id='price-change'),
                        html.H3(children='', id='price-change'),
                      ],
                      align='right'
                     )
                       
        self.app.layout = html.Div(children=[
            html.H1(children='Stock Prices'),

            #dbc.Alert("This is a primary alert", color="primary"),

            html.Br(),
            #html.Div(children='''
            #    Dash: A web application framework for Python.
            #'''),

            data_list,
            navbar,
            symbol_info,

            #html.Datalist(
            #    id=self.com['sym']['suggest'], 
            #    children=[html.Option(value=word) 
            #                for word in DB.get_symbols_names_from_mongo()]
            #),
            #dcc.Input(id=self.com['sym']['input'],
            #    type='text',
            #    list=self.com['sym']['suggest'],
            #    placeholder='Enter a Stock Symbol',
            #    size='30',
            #    value=''
            #),
            html.Data("                "),
            html.Data("                "),
            html.Data("                "),
            html.Data("                "),
            html.Data("                "),
        
            ##html.Button('Submit', id=self.com['sym']['button']),
            #dbc.Button("Submit", id=self.com['sym']['button'], outline=True, color="primary", className="mr-1"),

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
        self.fin = {'income': pd.DataFrame(),
                    'balance': pd.DataFrame(),
                    'cash': pd.DataFrame()
                    }
        self.quart_fin = {'income': pd.DataFrame(),
                    'balance': pd.DataFrame(),
                    'cash': pd.DataFrame()
                    }

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
                   'Close',
                   'Low', 
                   'High', 
                   'Adj Close',
                   'Volume'
                ]
        self.df  = DB.get_stock_prices(self.symbol, columns=columns)
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

