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

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv')

fig = px.line(df, x='Date', y='AAPL.High', title='Time Series with Rangeslider')

fig.update_xaxes(rangeslider_visible=True)
#fig.show()

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph'
    )
])

@app.callback(
    Output('example-graph', 'figure'),
    [Input('example-graph', 'value')])
def update_figure(value):
    print("Entering Call back")
    print(value)
#    graph_df = df.iloc[value[0]:value[1]]
#    line_graph = go.Scatter(
#            x = graph_df.index[value[0]:value[1]],
#            y = graph_df['Adj Close'][value[0]:value[1]]
#            #x = df.index,
#            #y = df['Adj Close']
#            )
#    
#    layout = go.Layout(
#            paper_bgcolor='#27293d',
#            plot_bgcolor='rgba(0,0,0,0)',
#            xaxis=dict(type='category'),
#            yaxis=dict(range=[graph_df['Adj Close'].min(), graph_df['Adj Close'].max()], autorange=True),
#            font=dict(color='white'),
#            )
#
#    data = [line_graph]
#
#    return {'data':data, 'layout':layout}

    #graph_df = df.iloc[value[0]:value[1]]

    #fig = px.line(df, x='Date', y='AAPL.High', title='Time Series with Rangeslider')
    #fig = px.line(graph_df, x='Date', y='Adj Close', title='Time Series with Range Slider and Selectors')
    #fig = px.line(graph_df, x='Date', y='Adj Close', title='Time Series with Range Slider and Selectors', log_x=True)

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
    #fig.update_yaxes()

    fig.update_layout(transition_duration=500, yaxis=dict(autorange=True))
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
