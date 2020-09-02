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
import pprint

pp = pprint.PrettyPrinter(indent=4)

def zoom(layout, xrange):
#def zoom(layout, xrange, yrange):
    print("calling zoom")
    df.to_excel("/home/vpetla/desire.xls")
    #print("%s-%s" % (xrange, yrange))
    in_view = df.loc[fig.layout.xaxis.range[0]:fig.layout.xaxis.range[1]]
    fig.layout.yaxis.range = [in_view.High.min() - 10, in_view.High.max() + 10]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
query = 'select Date, `Adj Close`, `Volume` from {} order by Date'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
DB.close_sql_connection(mysql_engine)
graph_df = df

#fig = px.line(df, x="Date", y="Adj Close", title='Price Graph')
#fig.update_xaxes(
#    rangeslider_visible=True,
#    rangeselector=dict(
#        buttons=list([
#            dict(count=1, label="1m", step="month", stepmode="backward"),
#            dict(count=6, label="6m", step="month", stepmode="backward"),
#            dict(count=1, label="YTD", step="year", stepmode="todate"),
#            dict(count=1, label="1y", step="year", stepmode="backward"),
#            dict(step="all")
#        ])
#    )
#)
#fig.layout.on_change(zoom, 'xaxis.range')

#fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

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

    html.P(id='place'),

    dcc.RangeSlider(
        id='range-slider',
        #min = min_year, 
        #max = max_year, 
        min = 0,
        max = len(graph_df.index),
        step = None,
        marks=date_list,
        #allowCross=True,
        value = [0, len(graph_df.index)]
    )
])

@app.callback(
    Output('candle-graph', 'figure'),
    [Input('range-slider', 'value')])
def update_figure(value):

    print("values:{},{}".format(value[0], value[1]))
    print(type(value[0]), type(value[1]))
    #start = dt.strptime(str(value[0]), "%Y").date()
    #print("start: %r" %(start))
    #start = hdf5.get_nearest_index(df, start)
    #print("start: %r" %(start))
    #end = dt.strptime(str(value[1]), "%Y").date()
    #print("end: %r" %(end))
    #end = hdf5.get_nearest_index(df, end)
    #print("end: %r" %(end))

    #print("start: %r" %(start))
    #print("end: %r" %(end))
    #print(type(start))
    #print(type(end))
    graph_df = df.iloc[value[0]:value[1]]

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
            margin=dict(autoexpand=True),
            xaxis=dict(
                       rangeselector=dict(
                          buttons=list([
                              dict(count=1, label="1m", step="month", stepmode="backward"),
                              dict(count=6, label="6m", step="month", stepmode="backward"),
                              dict(count=1, label="YTD", step="year", stepmode="todate"),
                              dict(count=1, label="1y", step="year", stepmode="backward"),
                              dict(step="all")
                          ])
                       ),
                       rangeslider=dict(visible=True),
                       #range=[graph_df.index.min(), graph_df.index.max()], 
                       autorange=True, 
                       #automargin=True,
                       #fixedrange=False,
                       type="date"
                       ),
            yaxis=dict(
                       #range=[graph_df['Adj Close'].min(), graph_df['Adj Close'].max()], 
                       autorange=True, 
                       #automargin=True,
                       #fixedrange=False
                      ),
                      #font=dict(color='white'),
            )

    data = [line_graph]

    fig = go.Figure(data, layout)
    #fig.layout.on_change(zoom, 'xaxis.range')
    #fig.layout.on_change(zoom, ('xaxis', 'range'), ('yaxis', 'range'))
    #print("Layout xrange {0}".format(fig.layout.xaxis.range))
    pp.pprint(fig)
    #print("X Range: %r" %(layout.xaxis.range))
    #print("Y Range: %r" %(layout.yaxis.range))
    #fig = go.Figure(go.Scatter(x=[1, 2], y=[1, 0]))
    #fig.layout.on_change(
    #     lambda obj, xrange, yrange: print("%s-%s" % (xrange, yrange)),
    #     ('xaxis', 'range'), ('yaxis', 'range'))
    return fig
    #return {'data':data, 'layout':layout}
#
#    graph_df = df.iloc[value[0]:value[1]]
#
#    fig = px.line(graph_df, x='Date', y='Adj Close', title='Time Series with Range Slider and Selectors')
#    #fig = px.line(graph_df, x='Date', y='Adj Close', title='Time Series with Range Slider and Selectors', log_x=True)
#
#    #fig.update_xaxes(
#    #    rangeslider_visible=True,
#    #    rangeselector=dict(
#    #        buttons=list([
#    #            dict(count=1, label="1m", step="month", stepmode="backward"),
#    #            dict(count=6, label="6m", step="month", stepmode="backward"),
#    #            dict(count=1, label="YTD", step="year", stepmode="todate"),
#    #            dict(count=1, label="1y", step="year", stepmode="backward"),
#    #            dict(step="all")
#    #        ])
#    #    )
#    #)
#    #fig.update_yaxes()
#
#    fig.update_layout(transition_duration=500)
#    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
