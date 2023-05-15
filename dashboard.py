import DB
import hdf5

import dash
from dash import html
from dash import dcc
#import dash_core_components as dcc
#import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_elasticsearch_autosuggest as dea

import plotly.express as px
import plotly.graph_objs as go

from datetime import date, timedelta, datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd
import pprint
import pandas_ta as ta
import numpy as np
import copy

from dashcore import *

pp = pprint.PrettyPrinter(indent=4)

db = DashBoard()
items = DB.get_symbols_names_from_mongo()

@db.app.callback(
    Output(db.p_graph_id, 'figure'),
    [Input(db.p_graph_id, 'relayoutData'),
     Input(db.com['sym']['button'], 'n_clicks')],
    [State(db.com['sym']['input'], 'value')]
   )
def price_graph(points, n_clicks, symbol):
    global db
    print("Hover Value : {}".format(points))
    #if points:
    #    print("Hover keys : {}".format(points.keys()))

    if symbol:
        symbol = symbol.split(" ")[0]
    #print("Symbol: {}, N_Clicks: {}".format(symbol, n_clicks))
    if db.stock.symbol != symbol:
        db.stock.symbol = symbol

    if not db.stock.symbol:
        db.fig = go.Figure([], None)
        #db.fig = go.Figure([], go.Layout())
        return db.fig 

    ctx = dash.callback_context
    #print(ctx.triggered)
    if ctx.triggered:
        id = ctx.triggered[0]['prop_id'].split('.')[1]
        #print("ID: {}".format(id))

    #print("Points: {}".format(points))
    graph_df = db.stock.df
    if not points:
        raise PreventUpdate
    if id != 'n_clicks' and len(points.keys()) == 1 and 'yaxis.range' in points.keys():
        print("Returning with no update")
        raise PreventUpdate

    start, end = get_start_end(db.stock.df, points)
    if start and end:
        graph_df = db.stock.df.loc[start:end]

    db.p_graph['rsi_sell'] = go.Scatter(
           x = graph_df['Adj Close'][graph_df['RSI']>70].index,
           y = graph_df['Adj Close'][graph_df['RSI']>70],
           name = 'RSI Sell',
           mode = 'markers',
           marker = dict(size=10),
           fillcolor = 'rgb(128,0,0)',
           )

    db.p_graph['rsi_buy'] = go.Scatter(
           x = graph_df['Adj Close'][graph_df['RSI']<35].index,
           y = graph_df['Adj Close'][graph_df['RSI']<35],
           mode = 'markers',
           marker = dict(size=10),
           name = 'RSI Buy',
           fillcolor = 'rgb(0,128,0)'
           #visible = 'legendonly'
           )

    db.p_graph['mfi_sell'] = go.Scatter(
           x = graph_df['Adj Close'][graph_df['MFI']>80].index,
           y = graph_df['Adj Close'][graph_df['MFI']>80],
           name = 'MFI Sell',
           mode = 'markers',
           marker = dict(size=10),
           fillcolor = 'rgb(128,1,0)',
           )

    db.p_graph['mfi_buy'] = go.Scatter(
           x = graph_df['Adj Close'][graph_df['MFI']<21].index,
           y = graph_df['Adj Close'][graph_df['MFI']<21],
           mode = 'markers',
           marker = dict(size=10),
           name = 'MFI Buy',
           fillcolor = 'rgb(111,128,0)'
           #visible = 'legendonly'
           )

    db.p_graph['sma_buy'] = go.Scatter(
           x = graph_df['Adj Close'].index,
           y = graph_df['SMA_Buy'],
           mode = 'markers',
           marker = dict(size=10),
           name = 'SMA Buy',
           fillcolor = 'rgb(2,52,0)'
           #visible = 'legendonly'
           )

    db.p_graph['sma_sell'] = go.Scatter(
           x = graph_df['Adj Close'].index,
           y = graph_df['SMA_Sell'],
           mode = 'markers',
           marker = dict(size=10),
           name = 'SMA Sell',
           fillcolor = 'rgb(3,12,0)'
           #visible = 'legendonly'
           )

    db.p_graph['line'] = go.Scatter(
            x = graph_df.index,
            y = graph_df['Adj Close'],
            line=dict(color='royalblue', width=4),
            name = 'Price'
            )
    db.p_graph['rsi'] = go.Scatter(
            x = graph_df.index,
            y = graph_df['RSI'],
            name = 'RSI',
            line=dict(dash='dot'),
            fillcolor = 'rgb(100,128,0)'
            )
    db.p_graph['mfi'] = go.Scatter(
            x = graph_df.index,
            y = graph_df['MFI'],
            name = 'MFI',
            line=dict(dash='dot'),
            fillcolor = 'rgb(100,128,0)'
            )
    db.p_graph['sma30'] = go.Scatter(
            x = graph_df.index,
            y = graph_df['SMA30'],
            name = 'SMA30',
            fillcolor = 'rgb(1,128,0)'
            #visible = 'legendonly'
            )
    db.p_graph['sma100'] = go.Scatter(
            x = graph_df.index,
            y = graph_df['SMA100'],
            name = 'SMA100',
            fillcolor = 'rgb(2,128,0)'
            #visible = 'legendonly'
            )
 
    #db.p_graph['candlestick'] = go.Candlestick(
    #        x = graph_df.index,
    #        open = graph_df['Open'] + 50,
    #        high = graph_df['High'] + 50,
    #        low  = graph_df['Low']  + 50,
    #        close= graph_df['Close']+ 50,
    #        increasing = {'line': {'color' : '#00CC94'}},
    #        decreasing = {'line': {'color' : '#F50030'}},
    #        name = 'Candlestick',
    #        visible = 'legendonly'
    #        )


    #for k in list(db.p_graph_prop.keys())[1:]:
    #    print(k, db.p_graph_prop[k])
    #    if 'visible' not in db.p_graph_prop[k].keys():
    #        db.p_graph_prop[k]['visible'] = 'legendonly'
    #        db.p_graph[k]['visible'] = 'legendonly'

    data = [db.p_graph['line']]
    data.append(db.p_graph['rsi'])
    data.append(db.p_graph['rsi_sell'])
    data.append(db.p_graph['rsi_buy'])
    data.append(db.p_graph['mfi'])
    data.append(db.p_graph['mfi_sell'])
    data.append(db.p_graph['mfi_buy'])
    data.append(db.p_graph['sma30'])
    data.append(db.p_graph['sma100'])
    data.append(db.p_graph['sma_buy'])
    data.append(db.p_graph['sma_sell'])

    y_min = min(graph_df['Adj Close'].min(), graph_df['SMA30'].min(),  graph_df['SMA100'].min(), 0)
    y_max = max(graph_df['Adj Close'].max(), graph_df['SMA30'].max(),  graph_df['SMA100'].max(), 100)

    #layout = go.Layout()
    layout = go.Layout(
            #paper_bgcolor='#27293d',
            #plot_bgcolor='rgba(0,0,0,0)',
            #xaxis=dict(type='category'),
            width=2200,
            height=750,
            xaxis=dict(
                       calendar='gregorian',
                       rangeselector=dict(
                          buttons=list([
                              dict(count=1, label="1m", step="month", stepmode="backward"),
                              dict(count=3, label="3m", step="month", stepmode="backward"),
                              dict(count=6, label="6m", step="month", stepmode="backward"),
                              dict(count=1, label="YTD", step="year", stepmode="todate"),
                              dict(count=1, label="1y", step="year", stepmode="backward"),
                              dict(count=5, label="5y", step="year", stepmode="backward"),
                              dict(count=10, label="10y", step="year", stepmode="backward"),
                              dict(step="all")
                          ])
                       ),
                       #rangeslider=dict(visible=True,
                       #                 range=[df.index.min(), df.index.max()]), 
                       range=[
                           graph_df.index.min(), 
                           #graph_df.index.max()
                           str(dt.strptime(graph_df.index.max(), "%Y-%m-%d").date() + relativedelta(days=4))
                           ], 
                       #range=[graph_df.index[-90:].min(), graph_df[-90:].index.max()], 
                       #autorange=True, automargin=True,
                       fixedrange=False,
                       type="date"
                       ),
            yaxis=dict(range=[y_min-10, y_max], 
                       #autorange=True, 
                       #automargin=True,
                       fixedrange=False
                       #font=dict(color='white'),
                      ),
            #legend=dict(orientation='h',
            #            yanchor='bottom',
            #            y=1.02,
            #            xanchor='right',
            #            x=1)
            )
   # pp.pprint(layout)
     
    db.fig = go.Figure(data, layout)
    return db.fig 

if __name__ == '__main__':
    db.app.run_server(debug=True)
