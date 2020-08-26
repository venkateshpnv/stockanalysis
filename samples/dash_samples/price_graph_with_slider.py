import sys
sys.path.insert(1, '/home/vpetla/work/stockanalysis/')
import DB
import hdf5

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import plotly.express as px
import plotly.graph_objs as go

from datetime import date, timedelta, datetime as dt
import pandas as pd

def zoom(layout, xrange):
    in_view = df.loc[fig.layout.xaxis.range[0]:fig.layout.xaxis.range[1]]
    fig.layout.yaxis.range = [in_view.High.min() - 10, in_view.High.max() + 10]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
query = 'select Date, `Adj Close`, `Volume` from {} order by Date'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
DB.close_sql_connection(mysql_engine)
graph_df = df

years = len(pd.to_datetime(df.index).year.unique())
mark_divisions = years / 2
if mark_divisions < 2:
    mark_divisions = 4
mark_division_factor = int(len(df.index)/mark_divisions)

date_list = {i: str(d) for i, d in enumerate(pd.to_datetime(df.index).year.unique())}
date_list = {}
for i, d in enumerate(pd.to_datetime(df.index)):
    if i % int(len(df.index)/mark_divisions) == 0:
        date_list[i] = str(dt.strptime(str(d.year), "%Y").date())
date_list[i] = 'till_date'

print(date_list)
min_year = pd.to_datetime(graph_df.index[0]).year
max_year = pd.to_datetime(graph_df.index[-1]).year

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='candle-graph', animate=True, style={'backgroundColor':'#1a2d46', 'color':'#ffffff'},),

    html.Br(),
    html.Br(),
    html.Br(),

    html.P(id="p"),

    dcc.RangeSlider(
        id='range-slider',
        #min = min_year, 
        #max = max_year, 
        min = 0,
        max = len(graph_df.index),
        step = None,
        marks=date_list,
        #allowCross=True,
        value = [0, len(graph_df.index)],
        vertical=True,
        verticalHeight=400
    )
])

def get_start_end(df, points):
    # Return None for 'autosize', 'xaxis.autorange', None
    start = end = None

    if points:
        keys = points.keys()

        if len(keys) == 1 and 'yaxis.range' in keys:
            start = df[df['Adj Close'] == points['yaxis.range'][0]].index[0]
            end   = df[df['Adj Close'] == points['yaxis.range'][1]].index[0]
        elif 'xaxis.range' in keys:
            start = points['xaxis.range'][0].split(' ')[0].split('T')[0]
            end   = points['xaxis.range'][1].split(' ')[0].split('T')[0]
        elif 'xaxis.range[0]' in keys:
            start = points['xaxis.range[0]'].split(' ')[0].split('T')[0]
            end   = points['xaxis.range[1]'].split(' ')[0].split('T')[0]
    print("Start: %r, End: %r" %(start, end))
    return start, end 

@app.callback(
    #Output('p', 'title'),
    Output('candle-graph', 'figure'),
    [Input('candle-graph', 'relayoutData')])
def hover(points):
    print("Hover Value : {}".format(points))
    if points:
        print("Hover keys : {}".format(points.keys()))

    #if points == None or 'autosize' in points.keys() or 'xaxis.autorange' in points.keys():
    #    graph_df = df 
    #else:
    if True:
        graph_df = df
        start, end = get_start_end(df, points)
        if start and end:
            graph_df = df.loc[start:end]

    line_graph = go.Scatter(
            x = graph_df.index,
            y = graph_df['Adj Close']
            #x = graph_df.index[value[0]:value[1]],
            #y = graph_df['Adj Close'][value[0]:value[1]]
            #x = df.index,
            #y = df['Adj Close']
            )
  
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
                              dict(count=50, label="50y", step="year", stepmode="backward"),
                              dict(step="all")
                          ])
                       ),
                       rangeslider=dict(visible=True),
                       range=[graph_df.index.min(), graph_df.index.max()], 
                       #autorange=True, automargin=True,
                       fixedrange=False,
                       type="date"
                       ),
            yaxis=dict(range=[graph_df['Adj Close'].min(), 
                       graph_df['Adj Close'].max()], 
                       #autorange=True, 
                       #automargin=True,
                       fixedrange=False
                      ),
                      #font=dict(color='white'),
            )

    data = [line_graph]

    return {'data':data, 'layout':layout}

if __name__ == '__main__':
    app.run_server(debug=True)
