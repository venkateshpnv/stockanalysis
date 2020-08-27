import sys
sys.path.insert(1, '/home/vpetla/work/stockanalysis/')
import DB
import hdf5

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State

import plotly.express as px
import plotly.graph_objs as go

from datetime import date, timedelta, datetime as dt
import pandas as pd
import pprint
import pandas_ta as ta

pp = pprint.PrettyPrinter(indent=4)

def zoom(layout, xrange):
    in_view = df.loc[fig.layout.xaxis.range[0]:fig.layout.xaxis.range[1]]
    fig.layout.yaxis.range = [in_view.High.min() - 10, in_view.High.max() + 10]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA])
#app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def get_stock_data(symbol):
	mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
	query = 'select `Date`, `Open`, `Close`, `High`, `Low`, `Adj Close` from {} order by Date'.format('STK'+symbol)
	df = DB.read_from_sql(query, mysql_engine)
	DB.close_sql_connection(mysql_engine)
	return df

df = get_stock_data('AAPL')
df['RSI'] = ta.rsi(df['Adj Close'])
fig = None
df['SMA30']=df['Adj Close'].rolling(window=30).mean()
df['SMA100']=df['Adj Close'].rolling(window=100).mean()

#years = len(pd.to_datetime(df.index).year.unique())
#mark_divisions = years / 2
#if mark_divisions < 2:
#    mark_divisions = 4
#mark_division_factor = int(len(df.index)/mark_divisions)
#
#date_list = {i: str(d) for i, d in enumerate(pd.to_datetime(df.index).year.unique())}
#date_list = {}
#for i, d in enumerate(pd.to_datetime(df.index)):
#    if i % int(len(df.index)/mark_divisions) == 0:
#        date_list[i] = str(dt.strptime(str(d.year), "%Y").date())
#date_list[i] = 'till_date'
#
#print(date_list)
#min_year = pd.to_datetime(graph_df.index[0]).year
#max_year = pd.to_datetime(graph_df.index[-1]).year

app.layout = html.Div(children=[
    html.H1(children='Stock Prices'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Input(id='input-box', value='', type='text', placeholder='Enter a stock symbol', ),
    html.Button('Submit', id='button'),

    dcc.Graph(
        id='stock-graph',
        animate=True
        #style={'backgroundColor':'#1a2d46', 'color':'#ffffff'},
        )

])

def get_start_end(df, points):
    # Return None for 'autosize', 'xaxis.autorange', None
    start = end = None

    if points:
        keys = points.keys()

        if len(keys) == 1 and 'yaxis.range' in keys:
            #start = df[df['Adj Close'] == points['yaxis.range'][0]].index[0]
            start = df.iloc[(df['Adj Close']-points['yaxis.range'][0]).abs().argsort()[:2]].index[0]
            end   = df.index[-1]
        elif 'xaxis.range' in keys:
            start = points['xaxis.range'][0].split(' ')[0].split('T')[0]
            end   = points['xaxis.range'][1].split(' ')[0].split('T')[0]
        elif 'xaxis.range[0]' in keys:
            start = points['xaxis.range[0]'].split(' ')[0].split('T')[0]
            end   = points['xaxis.range[1]'].split(' ')[0].split('T')[0]
    print("Start: %r, End: %r" %(start, end))
    return start, end 

@app.callback(
    Output('stock-graph', 'figure'),
    #[Input('button', 'n_clicks')],
    #[State('input-box', 'value'), State('stock-graph', 'relayoutData')] 
    [Input('stock-graph', 'relayoutData')] 
    #],
    #[State('input-box', 'value')]
   )
def price_graph(points):
#def price_graph(n_clicks, symbol, points): # n_clicks, symbol):
    global df
    print("Hover Value : {}".format(points))
    if points:
        print("Hover keys : {}".format(points.keys()))

    #print("Symbol: %s" %(symbol))
    #if symbol:
    #    df = get_stock_data(symbol.upper())
    #    df['RSI'] = ta.rsi(df['Adj Close'])
    #    df['SMA30']=df['Adj Close'].rolling(window=30).mean()
    #    df['SMA100']=df['Adj Close'].rolling(window=100).mean()

    graph_df = df
    start, end = get_start_end(df, points)
    if start and end:
        graph_df = df.loc[start:end]

    sell_graph = go.Scatter(
           x = graph_df['Adj Close'][graph_df['RSI']>70].index,
           y = graph_df['Adj Close'][graph_df['RSI']>70],
           mode = 'markers',
           name = 'Sell',
           fillcolor = 'rgb(128,0,0)'
           )

    buy_graph = go.Scatter(
           x = graph_df['Adj Close'][graph_df['RSI']<35].index,
           y = graph_df['Adj Close'][graph_df['RSI']<35],
           mode = 'markers',
           name = 'Buy',
           fillcolor = 'rgb(0,128,0)'
           )

    line_graph = go.Scatter(
            x = graph_df.index,
            y = graph_df['Adj Close'],
            name = 'Price'
            #x = graph_df.index[value[0]:value[1]],
            #y = graph_df['Adj Close'][value[0]:value[1]]
            #x = df.index,
            #y = df['Adj Close']
            )
    sma30_graph = go.Scatter(
            x = graph_df.index,
            y = graph_df['SMA30'],
            name = 'SMA30',
            fillcolor = 'rgb(1,128,0)'
            #x = graph_df.index[value[0]:value[1]],
            #y = graph_df['Adj Close'][value[0]:value[1]]
            #x = df.index,
            #y = df['Adj Close']
            )
    sma100_graph = go.Scatter(
            x = graph_df.index,
            y = graph_df['SMA100'],
            name = 'SMA100',
            fillcolor = 'rgb(2,128,0)'
            #x = graph_df.index[value[0]:value[1]],
            #y = graph_df['Adj Close'][value[0]:value[1]]
            #x = df.index,
            #y = df['Adj Close']
            )
 
    #candlestick_graph = go.Candlestick(
    #        x = graph_df.index,
    #        open = graph_df['Open'] + 50,
    #        high = graph_df['High'] + 50,
    #        low  = graph_df['Low']  + 50,
    #        close= graph_df['Close']+ 50,
    #        increasing = {'line': {'color' : '#00CC94'}},
    #        decreasing = {'line': {'color' : '#F50030'}},
    #        name = 'Candlestick'
    #        ) 
    data = [line_graph, sell_graph, buy_graph, sma30_graph, sma100_graph]
    #data = [sell_graph, buy_graph, line_graph, candlestick_graph]

    y_min = min(graph_df['Adj Close'].min(), graph_df['SMA30'].min(),  graph_df['SMA100'].min())
    y_max = max(graph_df['Adj Close'].max(), graph_df['SMA30'].max(),  graph_df['SMA100'].max())

    #layout = go.Layout()
    layout = go.Layout(
            #paper_bgcolor='#27293d',
            #plot_bgcolor='rgba(0,0,0,0)',
            #xaxis=dict(type='category'),
            xaxis=dict(
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
                       range=[graph_df.index.min(), graph_df.index.max()], 
                       #range=[graph_df.index[-90:].min(), graph_df[-90:].index.max()], 
                       #autorange=True, automargin=True,
                       fixedrange=False,
                       type="date"
                       ),
            yaxis=dict(range=[y_min, y_max], 
                       #autorange=True, 
                       #automargin=True,
                       fixedrange=False
                      ),
                      #font=dict(color='white'),
            )
   # pp.pprint(layout)
     
    fig = go.Figure(data, layout)
    return fig 
    #return {'data':data, 'layout':layout}

if __name__ == '__main__':
    app.run_server(debug=True)
