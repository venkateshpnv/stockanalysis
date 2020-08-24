import sys
sys.path.insert(1, '/home/vpetla/work/stockanalysis/')
import DB
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime
import pandas as pd

#fig = go.Figure(go.Scatter(x=[1, 2], y=[1, 0]))
#fig.layout.on_change(
#  lambda obj, xrange, yrange: print("%s-%s" % (xrange, yrange)),
#  ('xaxis', 'range'), ('yaxis', 'range'))

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
query = 'select Date, `Adj Close`, `Volume` from {} order by Date'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
DB.close_sql_connection(mysql_engine)


# Make sure dates are in ascending order
# We need this for slicing in the callback below
df.sort_index(ascending=True, inplace=True)

def zoom(layout, xrange):
    print('updating y axis')
    in_view = df.loc[fig.layout.xaxis.range[0]:fig.layout.xaxis.range[1]]
    print(in_view.index)
    fig.layout.yaxis.range = [in_view['Adj Close'].min() - 10, in_view['Adj Close'].max() + 10]


trace = go.Scatter(x=list(df.index),
                   y=list(df['Adj Close']))

data = [trace]
layout = dict(
    title='Time series with range slider and selectors',
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label='1m',
                     step='month',
                     stepmode='backward'),
                dict(count=6,
                     label='6m',
                     step='month',
                     stepmode='backward'),
                dict(count=1,
                    label='YTD',
                    step='year',
                    stepmode='todate'),
                dict(count=1,
                    label='1y',
                    step='year',
                    stepmode='backward'),
                dict(step='all')
            ])
        ),
        rangeslider=dict(
            visible = True
        ),
        type='date'
    )
)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph'
    ),
    html.Br(),
    html.Br(),
    html.Br(),
    dcc.Input(id='input')
])



@app.callback(
    Output('example-graph', 'figure'),
    [Input('input', 'value')])
def update_figure(value):
   fig = go.FigureWidget(data=data, layout=layout)
   fig.layout.on_change(zoom, 'xaxis.range')
   return fig


if __name__ == '__main__':
    app.run_server(debug=True)
