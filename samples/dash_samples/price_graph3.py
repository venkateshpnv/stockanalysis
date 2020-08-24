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


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
query = 'select Date, `Adj Close`, `Volume` from {} order by Date'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
DB.close_sql_connection(mysql_engine)


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
    print("Entering Call back")
    print(value)

    fig = px.line(df, x='Date', y='Adj Close', title='Time Series with Rangeslider')
    fig["layout"].pop("updatemenus") # optional, drop animation buttons

    fig.update_layout(transition_duration=500, yaxis=dict(autorange=True))
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
