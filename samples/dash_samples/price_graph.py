import sys
sys.path.insert(1, '/home/vpetla/work/stockanalysis/')
import DB
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objs as go
from datetime import datetime
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

## assume you have a "long-form" data frame
## see https://plotly.com/python/px-arguments/ for more options
#df = pd.DataFrame({
#    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
#    "Amount": [4, 1, 2, 2, 4, 5],
#    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
#})

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
        ]),
    ),
    type="date"
)
fig.update_xaxes(rangeslider_visible=True)
fig.update_layout(yaxis=dict(autorange=True))

#fig.layout.on_change(zoom, 'xaxis.range')

#fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
