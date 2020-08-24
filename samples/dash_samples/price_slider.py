import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np

import sys
sys.path.insert(1, '/home/vpetla/work/stockanalysis/')
import DB

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
query = 'select Date, `Adj Close`, `Volume` from {} order by Date'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
DB.close_sql_connection(mysql_engine)
graph_df = df

#df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Graph(id='graph-with-slider'),
    #dcc.Slider(
    #    id='year-slider',
    #    min=df['year'].min(),
    #    max=df['year'].max(),
    #    value=df['year'].min(),
    #    marks={str(year): str(year) for year in df['year'].unique()},
    #    step=None
    #)
    dcc.RangeSlider(
        id='year-slider',
        min=pd.to_datetime(df.index[0]).year,
        max=pd.to_datetime(df.index[-1]).year,
        marks={str(year): str(year) for year in pd.to_datetime(df.index).year.unique()},
        step = 5,
        #value = [0, len(df.index)]
        #value=[df['year'].min(), df['year'].max()]
        value=[pd.to_datetime(df.index[0]).year, pd.to_datetime(df.index[-1]).year]
    )
])


@app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('year-slider', 'value')])
def update_figure(selected_year):
    print(selected_year)
    #filtered_df = df[df.year == selected_year]
    start=list(np.where(df.year==selected_year[0])[0])[0]
    end=list(np.where(df.year==selected_year[1])[0])[0]
    filtered_df = df.iloc[start:end]

    fig = px.line(df, x="Date", y="Adj Close", title='Price Graph')
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    fig.update_layout(transition_duration=500, yaxis=dict(autorange=True))

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)


